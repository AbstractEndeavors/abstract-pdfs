"""
abstract_pdfs.enrichment.config
================================
Configuration objects for the enrichment layer.

Two ideas:

``DescribeConfig``
    Controls the optional *vision* description step (Qwen2.5-VL via
    ``abstract_hugpy``).  Per the design brief it behaves "much like a create
    prompt" — it accepts many shapes and is freely overridable or disabled:

        None                      -> disabled
        "describe this page"      -> a prompt string, mode defaults to "auto"
        {"mode": "always", ...}   -> explicit field overrides
        DescribeConfig(...)       -> used as-is

``EnrichmentConfig``
    Controls provider resolution (in-process hugpy -> HTTP service -> local
    fallback) and the summariser / keyword presets.

Everything is plain ``dataclasses`` + stdlib so this module imports anywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional, Union

__all__ = ["DescribeConfig", "EnrichmentConfig", "DescribeLike"]


# ---------------------------------------------------------------------------
# Vision / describe configuration
# ---------------------------------------------------------------------------

DEFAULT_DESCRIBE_PROMPT = (
    "Describe this document page in 1-2 plain sentences for a reader browsing "
    "a library. State what the page contains (e.g. a math test, a diagram, a "
    "table, handwritten work) and its apparent topic. Do not transcribe it."
)


@dataclass
class DescribeConfig:
    """Configuration for the optional vision-model description step.

    ``mode``:
        ``"auto"``   — only caption from the image when OCR quality is poor
                       (``< ocr_quality_threshold``); otherwise use the text
                       summary.  This is the recommended hybrid behaviour.
        ``"always"`` — always caption from the image.
        ``"never"``  — never use the vision model (equivalent to disabled).
    """

    enabled: bool = True
    mode: str = "auto"                       # "auto" | "always" | "never"
    prompt: str = DEFAULT_DESCRIBE_PROMPT
    model_key: Optional[str] = None
    max_new_tokens: int = 128
    ocr_quality_threshold: float = 0.55
    # Free-form passthrough for whatever the vision backend may accept later.
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.enabled and self.mode != "never"

    def wants_vision(self, ocr_quality: float) -> bool:
        """Decide whether to invoke the vision model for this page."""
        if not self.active:
            return False
        if self.mode == "always":
            return True
        # auto
        return ocr_quality < self.ocr_quality_threshold

    @classmethod
    def parse(cls, value: "DescribeLike") -> "DescribeConfig":
        """Coerce the many accepted shapes into a DescribeConfig.

        ``None`` / ``False`` -> a disabled config (never errors).
        """
        if value is None or value is False:
            return cls(enabled=False, mode="never")
        if value is True:
            return cls()
        if isinstance(value, DescribeConfig):
            return value
        if isinstance(value, str):
            return cls(prompt=value)
        if isinstance(value, dict):
            known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
            kwargs = {k: v for k, v in value.items() if k in known}
            extra = {k: v for k, v in value.items() if k not in known}
            cfg = cls(**kwargs)
            if extra:
                cfg = replace(cfg, extra={**cfg.extra, **extra})
            return cfg
        raise TypeError(f"Cannot build DescribeConfig from {type(value)!r}")


# A describe option may be supplied as any of these.
DescribeLike = Union[None, bool, str, Dict[str, Any], DescribeConfig]


# ---------------------------------------------------------------------------
# Top-level enrichment configuration
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentConfig:
    """How abstract-pdfs reaches NLP enrichment, and with what presets."""

    # Provider resolution.  "auto" tries hugpy (in-process) -> http -> local.
    mode: str = "auto"               # "auto" | "hugpy" | "http" | "local"

    # HTTP service base (e.g. "https://host/hugpy").  Endpoints are appended:
    #   {base}/analyze/text, {base}/summarizer/summarize, {base}/keybert/refine_keywords
    http_endpoint: Optional[str] = None
    http_timeout: float = 60.0

    # Summariser / keyword presets understood by abstract_hugpy.
    summary_preset: str = "article"     # whole-document
    page_summary_preset: str = "brief"  # single page
    keyword_preset: str = "seo"

    # Keyword cleaning gate applied to *every* provider's output.
    keyword_quality_threshold: float = 0.5
    max_meta_keywords: int = 15

    # Optional vision description step (see DescribeConfig).
    describe: Optional[DescribeConfig] = None

    def __post_init__(self):
        # Normalise describe to a DescribeConfig (or None when disabled).
        if self.describe is not None and not isinstance(self.describe, DescribeConfig):
            self.describe = DescribeConfig.parse(self.describe)

    @classmethod
    def resolve(
        cls,
        config: Union[None, "EnrichmentConfig", Dict[str, Any]] = None,
        *,
        describe: "DescribeLike" = "__unset__",
    ) -> "EnrichmentConfig":
        """Return an EnrichmentConfig from None / dict / instance, then apply
        env defaults and an optional ``describe`` override."""
        if isinstance(config, EnrichmentConfig):
            cfg = config
        elif isinstance(config, dict):
            known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
            cfg = cls(**{k: v for k, v in config.items() if k in known})
        else:
            cfg = cls.from_env()

        if describe != "__unset__":
            cfg = replace(cfg, describe=DescribeConfig.parse(describe))
        return cfg

    @classmethod
    def from_env(cls) -> "EnrichmentConfig":
        """Build from environment variables, falling back to defaults.

        Recognised:
          ABSTRACT_HUGPY_MODE       -> mode
          ABSTRACT_HUGPY_URL        -> http_endpoint
          ABSTRACT_HUGPY_DESCRIBE   -> "1"/"true"/"always"/"auto"/"never"
        """
        mode = os.environ.get("ABSTRACT_HUGPY_MODE", "auto").strip() or "auto"
        endpoint = os.environ.get("ABSTRACT_HUGPY_URL") or None

        describe_env = os.environ.get("ABSTRACT_HUGPY_DESCRIBE")
        describe: Optional[DescribeConfig]
        if describe_env is None:
            describe = None
        else:
            v = describe_env.strip().lower()
            if v in ("0", "false", "no", "off", "none", "never", ""):
                describe = DescribeConfig(enabled=False, mode="never")
            elif v in ("always", "auto"):
                describe = DescribeConfig(mode=v)
            else:  # "1", "true", "on", "yes"
                describe = DescribeConfig(mode="auto")

        return cls(mode=mode, http_endpoint=endpoint, describe=describe)
