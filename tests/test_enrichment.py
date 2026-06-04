"""
Tests for abstract_pdfs.enrichment.

These exercise the pure-stdlib tiers (quality gate, local provider, document
aggregation, config parsing) — no ML models or network required.  They import
the ``enrichment`` package standalone so the suite runs even where the heavy
package dependencies (abstract_utilities, abstract_ocr, ...) are absent.
"""

import os
import sys

try:
    import pytest
except ImportError:  # allow running without pytest via the __main__ harness
    pytest = None

_ENRICH_PARENT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "abstract_pdfs"
)
if _ENRICH_PARENT not in sys.path:
    sys.path.insert(0, _ENRICH_PARENT)

from enrichment import quality, enrich_page, enrich_document  # noqa: E402
from enrichment.config import DescribeConfig, EnrichmentConfig  # noqa: E402


# --- the real OCR garbage from the reported example -------------------------

GARBAGE = [
    "math", "calculus", "teest", "b2%-", "lpreyy", "nualeer.|", "exp(x",
    "-abes", "tatvtte", "unttrvel", "compute", "rule", "gk-2", "20019",
]


def test_clean_keywords_drops_symbol_and_digit_junk():
    cleaned = quality.clean_keywords(GARBAGE)
    for junk in ("b2%-", "nualeer.|", "exp(x", "gk-2", "20019"):
        assert junk not in cleaned
    for good in ("math", "calculus", "compute", "rule"):
        assert good in cleaned


def test_clean_keywords_accepts_keybert_tuples():
    items = [("integrals sketching graph", 0.5), ("dx trapezoidal rule", 0.34)]
    cleaned = quality.clean_keywords(items)
    assert "integrals sketching graph" in cleaned


def test_token_quality_extremes():
    assert quality.token_quality("integral") > 0.6      # real word
    assert quality.token_quality("kx") < 0.5            # no/low vowels, short
    assert quality.token_quality("b2%-") == 0.0         # symbol/digit junk
    assert quality.token_quality("unttrvel") < 0.5      # long consonant run


def test_ocr_quality_clean_beats_noisy():
    clean = "Compute the following integrals by sketching the graph and stating their value."
    noisy = "fea de Bm Stes UT Ln Bod rl rot vii bm NF asa Nall nualeer Kx abes Tatvtte"
    assert quality.ocr_text_quality(clean) > quality.ocr_text_quality(noisy)
    assert quality.ocr_text_quality(clean) > 0.8


def test_extractive_summary_is_clean_and_nonempty():
    text = (
        "Compute the following integrals by sketching the graph. "
        "fea de Bm rl rot vii bm NF asa. "
        "State whether the sequence is increasing decreasing or bounded."
    )
    s = quality.extractive_summary(text, max_sentences=2, max_words=40)
    assert s
    assert "integrals" in s.lower() or "sequence" in s.lower()


# --- local provider end-to-end ---------------------------------------------

def test_enrich_page_local_fallback():
    text = "Compute the following integrals by sketching the graph and stating their value."
    res = enrich_page(text, scope="page:2", config={"mode": "local"})
    assert res["provider"] == "local"
    assert res["scope"] == "page:2"
    assert res["summary"]
    assert res["description_source"] == "summary"  # no vision configured
    assert res["keywords"]["primary"]
    # no junk leaked into meta keywords
    assert "%" not in res["keywords"]["meta_keywords"]
    assert isinstance(res["keywords"]["primary"], list)


def test_enrich_document_aggregates():
    pages = [
        "Compute the following integrals by sketching the graph.",
        "Determine whether each sequence is increasing decreasing or bounded.",
    ]
    doc = enrich_document(pages, config={"mode": "local"})
    assert doc["scope"] == "full"
    assert doc["page_count"] == 2
    assert doc["summary"]
    assert doc["keywords"]["primary"]


def test_enrich_page_keywords_never_dict_keys():
    """Regression: keywords must be a flat list of strings, never object keys."""
    res = enrich_page("integrals graph value sequence", config={"mode": "local"})
    kws = res["keywords"]["primary"]
    assert all(isinstance(k, str) for k in kws)
    # the bug emitted internal field names like 'density', 'density_flags'
    assert "density" not in kws and "density_flags" not in kws


# --- describe / vision config (the "create-prompt-like" option) -------------

def test_describe_config_parse_shapes():
    assert DescribeConfig.parse(None).active is False
    assert DescribeConfig.parse(False).active is False
    assert DescribeConfig.parse(True).active is True
    assert DescribeConfig.parse("caption this page").prompt == "caption this page"
    cfg = DescribeConfig.parse({"mode": "always", "max_new_tokens": 64, "foo": "bar"})
    assert cfg.mode == "always"
    assert cfg.max_new_tokens == 64
    assert cfg.extra["foo"] == "bar"


def test_describe_auto_uses_quality_threshold():
    cfg = DescribeConfig(mode="auto", ocr_quality_threshold=0.55)
    assert cfg.wants_vision(0.2) is True      # poor OCR -> caption from image
    assert cfg.wants_vision(0.9) is False     # good OCR -> text summary
    assert DescribeConfig(mode="always").wants_vision(0.99) is True
    assert DescribeConfig(mode="never").wants_vision(0.0) is False


def test_enrichment_config_resolve_and_env(monkeypatch):
    monkeypatch.setenv("ABSTRACT_HUGPY_MODE", "local")
    monkeypatch.setenv("ABSTRACT_HUGPY_URL", "https://example.test/hugpy")
    cfg = EnrichmentConfig.from_env()
    assert cfg.mode == "local"
    assert cfg.http_endpoint == "https://example.test/hugpy"
    # describe override applied through resolve
    cfg2 = EnrichmentConfig.resolve({"mode": "local"}, describe="caption it")
    assert cfg2.describe is not None and cfg2.describe.prompt == "caption it"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
