"""
abstract_pdfs.enrichment.providers
===================================
Pluggable enrichment providers, resolved in this order by ``mode="auto"``:

    1. ``HugpyProvider``  — in-process ``abstract_hugpy`` (best quality).
    2. ``HttpProvider``   — a hugpy HTTP service (when ``http_endpoint`` set).
    3. ``LocalProvider``  — pure-stdlib fallback (always works).

Each provider returns a normalised intermediate ``RawAnalysis``; the cleaning /
SEO-shaping into the final result dict happens once, in ``enrich.py``, so every
tier gets the same keyword-quality gate.

Heavy / optional imports (abstract_hugpy, requests/abstract_apis) are performed
lazily inside methods so importing this module never drags them in.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import DescribeConfig, EnrichmentConfig
from . import quality

logger = logging.getLogger("abstract_pdf.enrichment")

__all__ = [
    "RawAnalysis",
    "BaseProvider",
    "HugpyProvider",
    "HttpProvider",
    "LocalProvider",
    "resolve_provider",
    "vision_caption",
]


@dataclass
class RawAnalysis:
    """Provider-agnostic analysis result, pre-cleaning."""
    summary: str = ""
    keyword_candidates: List[Any] = field(default_factory=list)
    keywords_obj: Optional[Dict[str, Any]] = None  # rich dict if provider has one
    provider: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------

class BaseProvider:
    name = "base"

    def available(self) -> bool:
        return True

    def analyze(self, text: str, scope: str, cfg: EnrichmentConfig) -> RawAnalysis:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 1. In-process abstract_hugpy
# ---------------------------------------------------------------------------

class HugpyProvider(BaseProvider):
    name = "hugpy"

    @staticmethod
    def _imports():
        # Returns (summarize, refine_keywords) or raises ImportError.
        try:
            from abstract_hugpy import summarize, refine_keywords  # type: ignore
            return summarize, refine_keywords
        except Exception:
            from abstract_hugpy.managers.summarizers.summarizers import summarize  # type: ignore
            from abstract_hugpy.managers.keywords.keybert_model import refine_keywords  # type: ignore
            return summarize, refine_keywords

    def available(self) -> bool:
        try:
            self._imports()
            return True
        except Exception as exc:
            logger.debug("hugpy unavailable: %s", exc)
            return False

    def analyze(self, text: str, scope: str, cfg: EnrichmentConfig) -> RawAnalysis:
        summarize, refine_keywords = self._imports()
        preset = cfg.page_summary_preset if scope.startswith("page") else cfg.summary_preset

        summary = ""
        try:
            summary = summarize(text, preset=preset) or ""
        except Exception as exc:
            logger.warning("hugpy summarize failed (%s); using extractive fallback", exc)
            summary = quality.extractive_summary(text, **_local_summary_kwargs(preset))

        keywords_obj: Optional[Dict[str, Any]] = None
        candidates: List[Any] = []
        try:
            refined = refine_keywords(text, preset=cfg.keyword_preset)
            keywords_obj = _refined_to_dict(refined)
            candidates = list(keywords_obj.get("primary") or []) + list(
                keywords_obj.get("secondary") or []
            )
        except Exception as exc:
            logger.warning("hugpy refine_keywords failed (%s); using local keywords", exc)
            candidates = _local_keyword_candidates(text)

        return RawAnalysis(
            summary=summary,
            keyword_candidates=candidates,
            keywords_obj=keywords_obj,
            provider=self.name,
            raw={"summary_preset": preset, "keyword_preset": cfg.keyword_preset},
        )


def _refined_to_dict(refined) -> Dict[str, Any]:
    """Normalise a hugpy RefinedResult (dataclass or dict) to a plain dict."""
    if isinstance(refined, dict):
        return refined
    keys = (
        "primary", "secondary", "dropped", "density", "density_flags",
        "meta_keywords", "hashtags", "slug_candidates", "preset_used",
    )
    out: Dict[str, Any] = {}
    for k in keys:
        if hasattr(refined, k):
            out[k] = getattr(refined, k)
    return out


# ---------------------------------------------------------------------------
# 2. HTTP service
# ---------------------------------------------------------------------------

class HttpProvider(BaseProvider):
    name = "http"

    def __init__(self, endpoint: str, timeout: float = 60.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _post(url: str, data: dict, timeout: float) -> Any:
        # Prefer the project's abstract_apis helper; fall back to requests.
        try:
            from abstract_apis import postRequest  # type: ignore
            return postRequest(url, data=data)
        except Exception:
            import requests  # type: ignore
            resp = requests.post(url, json=data, timeout=timeout)
            resp.raise_for_status()
            return resp.json()

    def available(self) -> bool:
        return bool(self.endpoint)

    def analyze(self, text: str, scope: str, cfg: EnrichmentConfig) -> RawAnalysis:
        preset = cfg.page_summary_preset if scope.startswith("page") else cfg.summary_preset
        payload = {
            "text": text,
            "scope": scope,
            "summary_preset": preset,
            "keyword_preset": cfg.keyword_preset,
        }
        result = self._post(f"{self.endpoint}/analyze/text", payload, self.timeout) or {}
        if not isinstance(result, dict):
            result = {}

        keywords_obj = result.get("keywords")
        if not isinstance(keywords_obj, dict):
            keywords_obj = None
        candidates: List[Any] = []
        if keywords_obj:
            candidates = list(keywords_obj.get("primary") or []) + list(
                keywords_obj.get("secondary") or []
            )

        return RawAnalysis(
            summary=result.get("summary") or "",
            keyword_candidates=candidates,
            keywords_obj=keywords_obj,
            provider=self.name,
            raw={"endpoint": self.endpoint},
        )


# ---------------------------------------------------------------------------
# 3. Local pure-stdlib fallback
# ---------------------------------------------------------------------------

def _local_summary_kwargs(preset: str) -> dict:
    table = {
        "headline": dict(max_sentences=1, max_words=25),
        "brief":    dict(max_sentences=2, max_words=60),
        "article":  dict(max_sentences=5, max_words=180),
    }
    return table.get(preset, dict(max_sentences=3, max_words=80))


def _local_keyword_candidates(text: str, top_n: int = 20) -> List[str]:
    """Frequency + quality scored single-word candidates (no model)."""
    import re as _re
    from collections import Counter

    _STOP = {
        "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with",
        "is", "are", "was", "were", "that", "this", "it", "at", "by", "from",
        "as", "be", "has", "had", "its", "not", "but", "can", "we", "they",
        "their", "our", "if", "then", "than", "which", "whether", "each",
        "following", "determine", "compute", "show", "use", "first",
    }
    words = _re.findall(r"[A-Za-z][A-Za-z'\-]+", text.lower())
    freq = Counter()
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        if quality.token_quality(w) < 0.6:
            continue
        freq[w] += 1
    ranked = sorted(freq, key=lambda k: (freq[k], len(k)), reverse=True)
    return ranked[:top_n]


class LocalProvider(BaseProvider):
    name = "local"

    def analyze(self, text: str, scope: str, cfg: EnrichmentConfig) -> RawAnalysis:
        preset = cfg.page_summary_preset if scope.startswith("page") else cfg.summary_preset
        summary = quality.extractive_summary(text, **_local_summary_kwargs(preset))
        candidates = _local_keyword_candidates(text)
        return RawAnalysis(
            summary=summary,
            keyword_candidates=candidates,
            keywords_obj=None,
            provider=self.name,
            raw={"summary_preset": preset, "note": "local stdlib fallback"},
        )


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def resolve_provider(cfg: EnrichmentConfig) -> BaseProvider:
    """Pick a provider per ``cfg.mode``.

    ``auto`` walks hugpy -> http -> local and returns the first available.
    An explicit mode that turns out unavailable degrades gracefully to local
    rather than raising, so a batch never dies on a missing dependency.
    """
    if cfg.mode == "local":
        return LocalProvider()

    if cfg.mode == "hugpy":
        p = HugpyProvider()
        return p if p.available() else LocalProvider()

    if cfg.mode == "http":
        if cfg.http_endpoint:
            return HttpProvider(cfg.http_endpoint, cfg.http_timeout)
        logger.warning("mode=http but no http_endpoint configured; using local")
        return LocalProvider()

    # auto
    hp = HugpyProvider()
    if hp.available():
        return hp
    if cfg.http_endpoint:
        return HttpProvider(cfg.http_endpoint, cfg.http_timeout)
    return LocalProvider()


# ---------------------------------------------------------------------------
# Vision captioning (independent of the text provider)
# ---------------------------------------------------------------------------

def vision_caption(image_path: str, describe: DescribeConfig) -> Optional[str]:
    """Caption a page image via abstract_hugpy's vision model.

    Returns the caption string, or None if the vision stack is unavailable or
    the call fails — callers must treat None as "no vision description".
    """
    if not describe or not describe.active or not image_path:
        return None
    try:
        from abstract_hugpy import deepcoder_image_analysis  # type: ignore
    except Exception:
        try:
            from abstract_hugpy.managers.vision.vision_coder import (  # type: ignore
                deepcoder_image_analysis,
            )
        except Exception as exc:
            logger.debug("vision model unavailable: %s", exc)
            return None
    try:
        kwargs: Dict[str, Any] = {
            "prompt": describe.prompt,
            "max_new_tokens": describe.max_new_tokens,
        }
        if describe.model_key:
            kwargs["model_key"] = describe.model_key
        kwargs.update(describe.extra or {})
        text = deepcoder_image_analysis(image_path, **kwargs)
        return (text or "").strip() or None
    except Exception as exc:
        logger.warning("vision caption failed for %s: %s", image_path, exc)
        return None
