"""
abstract_pdfs.enrichment.enrich
===============================
High-level entry points the rest of abstract-pdfs calls.

    enrich_page(text, image_path=..., scope="page:N", config=...)
    enrich_document(page_texts=[...], config=...)

Both return a normalised result dict whose shape is backwards-compatible with
what the old ``clownworld.biz/hugpy/analyze/text`` endpoint returned, so the
HTML/manifest consumers need only minimal changes:

    {
      "scope": "page:2",
      "summary": "...",                  # text summary
      "description": "...",              # what to publish (vision caption or summary)
      "description_source": "vision|summary",
      "ocr_quality": 0.82,
      "keywords": {                      # cleaned, junk-free
          "primary": [...], "secondary": [...], "dropped": [...],
          "meta_keywords": "a, b, c", "hashtags": [...],
          "slug_candidates": [...], "density": {...}, "density_flags": {...},
          "preset_used": "seo",
      },
      "provider": "hugpy|http|local",
      "text": "...",
    }

The keyword-quality gate is applied here, once, to *every* provider's output —
so even a stale HTTP service or a model that emitted OCR noise gets cleaned.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Union

from .config import DescribeConfig, DescribeLike, EnrichmentConfig
from . import providers, quality

__all__ = ["enrich_page", "enrich_document", "build_keyword_block"]

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


# ---------------------------------------------------------------------------
# Keyword block assembly + cleaning
# ---------------------------------------------------------------------------

def _slugify_kw(kw: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", kw.lower()).strip("-")
    return s


def _hashtag(kw: str) -> str:
    return "#" + re.sub(r"[^a-z0-9]+", "", kw.lower())


def _density(keywords: Sequence[str], text: str) -> Dict[str, float]:
    words = _WORD_RE.findall(text.lower())
    total = len(words) or 1
    counts = Counter(words)
    out: Dict[str, float] = {}
    for kw in keywords:
        first = kw.lower().split()[0] if kw.split() else kw.lower()
        out[kw] = round(100.0 * counts.get(first, 0) / total, 4)
    return out


def _density_flags(density: Dict[str, float]) -> Dict[str, str]:
    flags = {}
    for kw, d in density.items():
        if d <= 0.0:
            flags[kw] = "thin"
        elif d > 4.0:
            flags[kw] = "stuffed"
        else:
            flags[kw] = "ok"
    return flags


def build_keyword_block(
    raw: providers.RawAnalysis,
    text: str,
    cfg: EnrichmentConfig,
) -> Dict[str, Any]:
    """Clean provider keyword output and shape the SEO keyword block.

    Works whether the provider supplied a rich ``keywords_obj`` (hugpy/http) or
    only candidates (local).  The junk gate is always applied.
    """
    threshold = cfg.keyword_quality_threshold

    primary_src: List[Any] = []
    secondary_src: List[Any] = []
    obj = raw.keywords_obj or {}
    if obj:
        primary_src = list(obj.get("primary") or [])
        secondary_src = list(obj.get("secondary") or [])
    if not primary_src:
        primary_src = list(raw.keyword_candidates or [])

    # Clean both tiers; anything filtered out is reported as "dropped".
    all_before = [
        (k if isinstance(k, str) else (k[0] if isinstance(k, (tuple, list)) and k else ""))
        for k in (primary_src + secondary_src)
    ]
    primary = quality.clean_keywords(
        primary_src, threshold=threshold, max_keywords=cfg.max_meta_keywords
    )
    secondary = quality.clean_keywords(secondary_src, threshold=threshold)
    # Keep secondary disjoint from primary.
    seen = {k.lower() for k in primary}
    secondary = [k for k in secondary if k.lower() not in seen]

    kept = {k.lower() for k in primary + secondary}
    dropped = sorted({k for k in all_before if k and k.lower() not in kept})

    meta_list = primary[: cfg.max_meta_keywords]
    density = obj.get("density") if isinstance(obj.get("density"), dict) else None
    if not density:
        density = _density(primary + secondary, text)
    flags = obj.get("density_flags") if isinstance(obj.get("density_flags"), dict) else None
    if not flags:
        flags = _density_flags(density)

    return {
        "primary": primary,
        "secondary": secondary,
        "dropped": dropped,
        "meta_keywords": ", ".join(meta_list),
        "hashtags": [_hashtag(k) for k in meta_list],
        "slug_candidates": [_slugify_kw(k) for k in primary[:5] if _slugify_kw(k)],
        "density": density,
        "density_flags": flags,
        "preset_used": obj.get("preset_used", cfg.keyword_preset),
    }


# ---------------------------------------------------------------------------
# Page / document enrichment
# ---------------------------------------------------------------------------

def enrich_page(
    text: str,
    *,
    image_path: Optional[str] = None,
    scope: str = "page",
    config: Union[None, EnrichmentConfig, dict] = None,
    describe: DescribeLike = "__unset__",
) -> Dict[str, Any]:
    """Summarise + keyword + (optionally) vision-describe one page."""
    cfg = EnrichmentConfig.resolve(config, describe=describe)
    text = text or ""

    provider = providers.resolve_provider(cfg)
    raw = provider.analyze(text, scope, cfg)

    keywords = build_keyword_block(raw, text, cfg)
    ocr_q = quality.ocr_text_quality(text)

    # Decide the published description: vision caption (when warranted &
    # available) else the text summary.
    description = raw.summary
    description_source = "summary"
    if cfg.describe and cfg.describe.wants_vision(ocr_q) and image_path:
        caption = providers.vision_caption(image_path, cfg.describe)
        if caption:
            description = caption
            description_source = "vision"

    return {
        "scope": scope,
        "summary": raw.summary,
        "description": description,
        "description_source": description_source,
        "ocr_quality": round(ocr_q, 4),
        "keywords": keywords,
        "provider": raw.provider,
        "text": text,
    }


def enrich_document(
    page_texts: Sequence[str],
    *,
    full_text: Optional[str] = None,
    config: Union[None, EnrichmentConfig, dict] = None,
    cover_image_path: Optional[str] = None,
    describe: DescribeLike = "__unset__",
) -> Dict[str, Any]:
    """Aggregate enrichment across a whole document.

    Produces a real document-level summary + merged keyword set, replacing the
    broken ``get_full_text_summary`` path (which raised NameError) and the
    static "Read X in image, text, or PDF view." description.
    """
    cfg = EnrichmentConfig.resolve(config, describe=describe)
    texts = [t for t in (page_texts or []) if t and t.strip()]
    doc_text = full_text if full_text is not None else "\n\n".join(texts)

    provider = providers.resolve_provider(cfg)
    raw = provider.analyze(doc_text, "full", cfg)

    keywords = build_keyword_block(raw, doc_text, cfg)
    ocr_q = quality.ocr_text_quality(doc_text)

    description = raw.summary
    description_source = "summary"
    if cfg.describe and cfg.describe.wants_vision(ocr_q) and cover_image_path:
        caption = providers.vision_caption(cover_image_path, cfg.describe)
        if caption:
            description = caption
            description_source = "vision"

    return {
        "scope": "full",
        "summary": raw.summary,
        "description": description,
        "description_source": description_source,
        "ocr_quality": round(ocr_q, 4),
        "keywords": keywords,
        "provider": raw.provider,
        "page_count": len(texts),
        "text": doc_text,
    }
