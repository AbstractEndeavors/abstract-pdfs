"""
Render-to-file helper.

Reads an optional template, builds the page, writes to disk.
"""
from __future__ import annotations
import os

from .builder import build_standalone_page
from .fileio import safe_write_text, safe_read_text


def render_to_file(meta_dict, body_html, out_path, template_path=None):
    """
    Build a page and write it to *out_path*.

    template_path – optional path to an HTML file containing
                    {{SEO_META}} and {{BODY}} placeholders.
    """
    template_html = None
    if template_path and os.path.isfile(template_path):
        template_html = safe_read_text(template_path)

    html = build_standalone_page(meta_dict, body_html, template_html)
    safe_write_text(out_path, html)
