"""
Gallery index page generation.

Renders a card-grid listing for a branch directory (collection of PDFs).
"""
from __future__ import annotations
import os

from ..config import DEFAULT_CONFIG
from ..fileio import (
    safe_read_json, safe_write_text, load_manifest,
    child_dirs, first_real_image, build_breadcrumbs,
)
from ..text import humanize, extract_description, extract_keywords_from_manifest
from ..urls import path_to_url
from ..jinja_env import get_jinja_env

GALLERY_TEMPLATE = "gallery.html.j2"


def _build_card(child, cfg):
    """Build one card dict for a child directory."""
    name = os.path.basename(child)
    manifest = load_manifest(child)

    card = {
        "href":  path_to_url(child, cfg.media_root, cfg.root_url) + "/",
        "title": humanize(name),
    }

    if manifest:
        card["description"] = extract_description(manifest)
        card["tags"] = extract_keywords_from_manifest(manifest, limit=5)
        card["page_count"] = len(manifest)

    # thumbnail: first image found recursively
    img_path = first_real_image(child, exts=list(cfg.image_exts))
    if img_path:
        card["image_url"] = path_to_url(img_path, cfg.media_root, cfg.root_url)

    return card


def get_gallery_page(directory, cfg=None):
    """
    Build and write the gallery index.html for a directory.

    Returns the rendered HTML string.
    """
    cfg = cfg or DEFAULT_CONFIG
    dir_name = os.path.basename(directory)
    base_url = path_to_url(directory, cfg.media_root, cfg.root_url)

    children = child_dirs(directory, skip=cfg.skip_dirs)
    cards = [_build_card(ch, cfg) for ch in children]

    env = get_jinja_env()
    template = env.get_template(GALLERY_TEMPLATE)

    html = template.render(
        page_title=humanize(dir_name),
        canonical_url=base_url + "/",
        breadcrumbs=build_breadcrumbs(base_url, cfg.root_url),
        heading=humanize(dir_name),
        card_count=len(cards),
        cards=cards,
    )

    html_path = os.path.join(directory, "index.html")
    safe_write_text(html_path, html)
    return html
