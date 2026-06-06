"""
Single image-page generation.

Renders the detail page for one page-image of a PDF.
"""
from __future__ import annotations
import json
import os

from ..config import DEFAULT_CONFIG
from ..fileio import safe_read_json, safe_read_text, safe_write_text, find_image_candidate, build_breadcrumbs
from ..text import humanize, clean_text, normalize_keyword_input
from ..urls import path_to_url
from ..meta import build_seo_html
from ..jinja_env import get_jinja_env

IMAGE_TEMPLATE = "image_page.html.j2"


def get_image_page(image_path, cfg=None):
    """
    Build and write index.html for a single page-image.

    image_path – absolute path to the image file (e.g. .../pages/3/image.png)
    Returns the rendered HTML string.
    """
    cfg = cfg or DEFAULT_CONFIG

    page_dir   = os.path.dirname(image_path)
    page_num   = os.path.basename(page_dir)
    pdf_dir    = os.path.dirname(page_dir)  # …/pages → …/
    # if page_dir is under a "pages/" subdir, pdf_dir is one more level up
    if os.path.basename(pdf_dir) == "pages":
        pdf_dir = os.path.dirname(pdf_dir)
    pdf_filename = os.path.basename(pdf_dir)
    pdf_basename = "{}.pdf".format(pdf_filename)
    pdf_path = os.path.join(pdf_dir, pdf_basename)

    # --- read per-page artifacts ---
    metadata = safe_read_json(os.path.join(page_dir, "metadata.json"))
    info     = safe_read_json(os.path.join(page_dir, "info.json"))
    text     = safe_read_text(os.path.join(page_dir, "text.txt"))

    # --- resolve image ---
    if not os.path.isfile(image_path):
        found = find_image_candidate(page_dir)
        if found:
            image_path = found

    image_url = path_to_url(image_path, cfg.media_root, cfg.root_url)

    # --- titles / descriptions ---
    title = metadata.get("title") or info.get("scope") or humanize(page_num)
    alt = metadata.get("alt") or "{} page {}".format(pdf_filename, page_num)
    description = metadata.get("description") or clean_text(text or alt, 220)
    keyword_tags = normalize_keyword_input(
        metadata.get("keywords")
        or (info.get("keywords") or {}).get("primary")
        or []
    )

    # --- URLs ---
    parent_pdf_url = path_to_url(pdf_dir, cfg.media_root, cfg.root_url)
    parent_pdf_file_url = path_to_url(pdf_path, cfg.media_root, cfg.root_url) if os.path.isfile(pdf_path) else ""

    # --- meta tags ---
    schema = metadata.get("schema") or {}
    metatags = build_seo_html(metadata)
    crumbs = build_breadcrumbs(image_url, cfg.root_url)

    license_text = "CC BY-SA 4.0 · Created by The Daily Dialectics for educational purposes"
    attribution = "@{}".format(cfg.site_name)

    # --- render ---
    env = get_jinja_env()
    template = env.get_template(IMAGE_TEMPLATE)

    html = template.render(
        metadata=metatags,
        schema_json=json.dumps(schema, ensure_ascii=False),
        breadcrumbs=crumbs,
        title=title,
        img_url=image_url,
        alt=alt,
        keyword_tags=keyword_tags,
        description=description,
        license=license_text,
        attribution=attribution,
        parent_pdf_url=parent_pdf_url,
        parent_pdf_file_url=parent_pdf_file_url,
        page_number=page_num,
        page_text=text,
        home_url=cfg.root_url,
    )

    html_path = os.path.join(page_dir, "index.html")
    safe_write_text(html_path, html)
    return html
