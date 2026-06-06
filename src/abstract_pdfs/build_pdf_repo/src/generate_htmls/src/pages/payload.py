"""
Per-page payload construction.

Reads the per-page artifacts (info.json, metadata.json, text.txt, images)
from a numbered page directory and returns a normalized dict that the
viewer and gallery builders consume.
"""
from __future__ import annotations
import os
import logging

from ..fileio import safe_read_json, safe_read_text, find_image_candidate
from ..urls import path_to_url
from ..config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def _extract_page_keywords(info):
    """Pull primary or meta_keywords list from info dict."""
    if not isinstance(info, dict):
        return []
    kw_block = info.get("keywords") or {}
    if not isinstance(kw_block, dict):
        return []
    return kw_block.get("primary") or kw_block.get("meta_keywords") or []


def _resolve_thumb(page_dir, meta, cfg):
    """Pick the best thumbnail URL for a page."""
    thumb = meta.get("thumbnail_resized") or meta.get("thumbnail_url_resized")
    image_url = meta.get("thumbnail") or meta.get("thumbnail_link")

    if thumb:
        # prefer a specific resized candidate, fall back to image_url
        candidate = find_image_candidate(page_dir, extra_candidates=["image_627x1200.png"])
        thumb = candidate or (image_url if image_url and os.path.isfile(image_url) else thumb)

    if not image_url:
        candidate = find_image_candidate(page_dir)
        image_url = candidate or thumb

    # convert local paths to URLs
    if thumb and os.path.isfile(thumb):
        thumb = path_to_url(thumb, cfg.media_root, cfg.root_url)
    if image_url and os.path.isfile(image_url):
        image_url = path_to_url(image_url, cfg.media_root, cfg.root_url)

    return thumb or "", image_url or ""


def build_page_payload(page_dir, pdf_slug, cfg=None):
    """
    Build the data dict for one numbered page directory.

    Returns::

        {
            "n":             int,
            "thumb":         str,   # thumbnail URL
            "image":         str,   # full image URL
            "text":          str,   # OCR / extracted text
            "alt":           str,
            "page_title":    str,
            "page_keywords": list[str],
        }
    """
    cfg = cfg or DEFAULT_CONFIG
    page_num = int(os.path.basename(page_dir))

    info_path = os.path.join(page_dir, "info.json")
    meta_path = os.path.join(page_dir, "metadata.json")
    text_path = os.path.join(page_dir, "text.txt")

    info = safe_read_json(info_path)
    meta = safe_read_json(meta_path)
    text = safe_read_text(text_path)

    page_keywords = _extract_page_keywords(info)
    title = meta.get("title") or ""

    thumb, image_url = _resolve_thumb(page_dir, meta, cfg)

    return {
        "n":             page_num,
        "thumb":         thumb,
        "image":         image_url,
        "text":          text,
        "alt":           title,
        "page_title":    title or (info.get("scope", "") if isinstance(info, dict) else ""),
        "page_keywords": page_keywords,
    }


def collect_pages(pages_dir, pdf_slug, cfg=None):
    """
    Walk the pages/ directory, build payloads for every numbered subdir.

    Returns (pages_list, aggregated_keywords).
    """
    cfg = cfg or DEFAULT_CONFIG
    pages = []
    all_keywords = []

    if not os.path.isdir(pages_dir):
        return pages, all_keywords

    for name in sorted(os.listdir(pages_dir)):
        page_dir = os.path.join(pages_dir, name)
        if not os.path.isdir(page_dir) or not name.isdigit():
            continue
        payload = build_page_payload(page_dir, pdf_slug, cfg)
        pages.append(payload)
        all_keywords.extend(payload["page_keywords"])

    return pages, all_keywords


def empty_page(pdf_slug):
    """Fallback single-page stub when no pages/ directory exists."""
    return {
        "n": 1,
        "thumb": "",
        "image": "",
        "text": "",
        "alt": pdf_slug,
        "page_title": "",
        "page_keywords": [],
    }
