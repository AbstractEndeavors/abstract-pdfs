"""
abstract_pdfs.enrichment
=========================
NLP enrichment for the PDF pipeline: summaries, SEO keywords and optional
vision descriptions, with a pluggable provider chain and an OCR-quality gate.

Provider resolution (``EnrichmentConfig.mode``):
    auto  -> in-process abstract_hugpy, else HTTP service, else local fallback
    hugpy -> in-process only (degrades to local if unavailable)
    http  -> HTTP service (degrades to local if no endpoint)
    local -> pure-stdlib fallback (no model dependencies)

Public API:
    enrich_page(text, image_path=..., scope="page:N", config=..., describe=...)
    enrich_document(page_texts=[...], config=..., describe=...)
    EnrichmentConfig, DescribeConfig
    quality.*  (ocr_text_quality, clean_keywords, extractive_summary, ...)
"""

from .config import DescribeConfig, EnrichmentConfig
from .enrich import build_keyword_block, enrich_document, enrich_page
from . import quality

__all__ = [
    "enrich_page",
    "enrich_document",
    "build_keyword_block",
    "EnrichmentConfig",
    "DescribeConfig",
    "quality",
]
