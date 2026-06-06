"""
PDF viewer page generation.

Orchestrates: payload collection → meta bundle → schema → Jinja render → write.
"""
from __future__ import annotations
import json
import os

from ..config import DEFAULT_CONFIG
from ..fileio import safe_read_json, safe_write_text, build_breadcrumbs
from ..text import humanize, clean_text, normalize_keywords
from ..urls import path_to_url
from ..meta import build_meta_bundle, build_schema
from ..jinja_env import get_jinja_env
from .payload import collect_pages, empty_page

VIEWER_TEMPLATE = "viewer/viewer_base.html"


def _resolve_canonical(pdf_dir, metadata, cfg):
    canonical = str(metadata.get("canonical") or "").strip()
    if canonical.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf")):
        return path_to_url(pdf_dir, cfg.media_root, cfg.root_url)
    if canonical:
        from ..urls import ensure_public_url
        return ensure_public_url(canonical, cfg.media_root, cfg.root_url)
    return path_to_url(pdf_dir, cfg.media_root, cfg.root_url)


def get_viewer_page(pdf_path, cfg=None):
    """
    Build and write the viewer index.html for a PDF.

    Returns the public URL of the PDF file.
    """
    cfg = cfg or DEFAULT_CONFIG

    pdf_dir  = os.path.dirname(pdf_path)
    pdf_slug = os.path.basename(pdf_dir)
    pages_dir = os.path.join(pdf_dir, "pages")
    html_path = os.path.join(pdf_dir, "index.html")
    meta_path = os.path.join(pdf_dir, "meta", "metadata.json")

    # --- metadata ---
    metadata = safe_read_json(meta_path)
    metadata["source_dir"] = pdf_dir

    title = metadata.get("title") or humanize(pdf_slug)
    description = clean_text(
        metadata.get("summary")
        or metadata.get("summary_html")
        or "Read {} in image, text, or PDF view.".format(title)
    )
    canonical_url = _resolve_canonical(pdf_dir, metadata, cfg)
    pdf_url = path_to_url(pdf_path, cfg.media_root, cfg.root_url)

    # --- pages ---
    pages, page_keywords = collect_pages(pages_dir, pdf_slug, cfg)
    if not pages:
        pages = [empty_page(pdf_slug)]

    keywords_list = normalize_keywords(metadata, page_keywords, limit=20)
    keywords_str = ", ".join(keywords_list)
    first_thumb = pages[0]["thumb"] if pages else ""

    # --- meta bundle + schema ---
    meta_bundle = build_meta_bundle(
        metadata=metadata,
        title=title,
        description=description,
        canonical_url=canonical_url,
        first_thumb=first_thumb,
        keywords_list=keywords_list,
        cfg=cfg,
    )

    schema = build_schema(
        metadata=metadata,
        title=title,
        description=description,
        canonical_url=canonical_url,
        meta_bundle=meta_bundle,
        keywords_list=keywords_list,
    )

    # --- viewer config (JS payload) ---
    viewer_config = {
        "title":       title,
        "description": description,
        "canonicalUrl": canonical_url,
        "siteRoot":    cfg.root_url,
        "pdfUrl":      pdf_url,
        "downloadUrl": pdf_url,
        "defaultMode": "images",
        "total":       len(pages),
        "keywords":    keywords_list,
        "pages":       pages,
    }

    # --- render ---
    env = get_jinja_env()
    template = env.get_template(VIEWER_TEMPLATE)
    thumbnail = meta_bundle["thumbnail_url"] or first_thumb

    html = template.render(
        title=title,
        description=description,
        keywords=keywords_str,
        canonical_url=canonical_url,
        first_thumb=thumbnail,
        schema_json=json.dumps(schema, ensure_ascii=False),
        site_root=cfg.root_url,
        pdf_url=pdf_url,
        download_url=pdf_url,
        total=len(pages),
        viewer_config_json=json.dumps(viewer_config, ensure_ascii=False),
        meta_bundle=meta_bundle,
        breadcrumbs=build_breadcrumbs(pdf_url, cfg.root_url),
        viewer_css_url="/assets/css/pdf-viewer/viewer.css",
        viewer_js_url="/assets/js/pdf-viewer/page-viewer.js",
        viewer_theme_vars="",
    )

    safe_write_text(html_path, html)
    return pdf_url
