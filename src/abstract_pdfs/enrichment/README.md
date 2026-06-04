# abstract_pdfs.enrichment

NLP enrichment for the PDF pipeline — summaries, SEO keywords and optional
vision descriptions — with a **pluggable provider chain** and an **OCR-quality
gate** so OCR noise (`teest`, `b2%-`, `nualeer.|`) never reaches published
metadata.

## Why

The pipeline previously POSTed raw OCR to a hard-coded
`https://clownworld.biz/hugpy/...` deployment and published whatever came back.
That produced junk keywords, weak descriptions, a broken document-level summary
(`NameError`) and `metadata.json` keywords that were actually the keyword
object's *dict keys*. This package replaces that path.

## Provider resolution

`EnrichmentConfig.mode` (default `"auto"`):

| mode    | behaviour                                                            |
|---------|---------------------------------------------------------------------|
| `auto`  | in-process `abstract_hugpy` → HTTP service → local fallback         |
| `hugpy` | in-process `abstract_hugpy` only (degrades to local if missing)     |
| `http`  | HTTP service at `http_endpoint` (degrades to local if unset)        |
| `local` | pure-stdlib fallback — no model dependencies, always works          |

A missing dependency never raises; it degrades to the next tier, so a batch
never dies on an environment that lacks the models.

## Usage

```python
from abstract_pdfs.enrichment import enrich_page, enrich_document

# one page (image_path enables the optional vision description)
res = enrich_page(ocr_text, image_path="…/page_002/image.png", scope="page:2")
res["summary"]                      # clean summary
res["description"]                  # vision caption when OCR is poor, else summary
res["keywords"]["primary"]          # cleaned keyword list
res["keywords"]["meta_keywords"]    # "a, b, c" for <meta name="keywords">

# whole document (aggregated)
doc = enrich_document(list_of_page_texts)
```

## Vision / describe option (configurable, like a create-prompt)

`describe=` accepts many shapes, or `None` to disable:

```python
enrich_page(text, image_path=img, describe=None)                 # disabled
enrich_page(text, image_path=img, describe=True)                 # auto mode
enrich_page(text, image_path=img, describe="Describe this page") # custom prompt
enrich_page(text, image_path=img, describe={                     # full control
    "mode": "always",          # "auto" | "always" | "never"
    "prompt": "…",
    "model_key": "qwen2.5-vl",
    "max_new_tokens": 128,
    "ocr_quality_threshold": 0.55,  # auto mode: caption when OCR quality < this
})
```

In `auto` mode the vision model is only invoked when `ocr_text_quality(text)`
falls below the threshold — clean pages keep their (cheaper) text summary.

## Environment variables

| var                       | meaning                                             |
|---------------------------|-----------------------------------------------------|
| `ABSTRACT_HUGPY_MODE`     | provider mode (`auto`/`hugpy`/`http`/`local`)       |
| `ABSTRACT_HUGPY_URL`      | HTTP service base, e.g. `https://host/hugpy`        |
| `ABSTRACT_HUGPY_DESCRIBE` | `auto`/`always`/`never` (or `1`/`0`) for vision     |

## Quality gate

`enrichment.quality` is pure stdlib and independently testable:

- `ocr_text_quality(text) -> 0..1` — drives the vision-fallback decision.
- `clean_keywords(items) -> [str]` — drops symbol/digit/improbable junk.
- `extractive_summary(text)` — the local-fallback summariser.

Accuracy improves automatically when `wordfreq` or a system word list is
importable (real misspellings like `teest` get caught); neither is required.
