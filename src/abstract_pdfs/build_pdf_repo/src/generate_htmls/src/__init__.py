"""
generate_htmls — static HTML generation for thedailydialectics.com

Public API
----------
Page builders:
    get_viewer_page(pdf_path, cfg=None)
    get_image_page(image_path, cfg=None)
    get_gallery_page(directory, cfg=None)

Standalone builder:
    build_standalone_page(meta_dict, body_html, template_html=None)
    render_to_file(meta_dict, body_html, out_path, template_path=None)

Configuration:
    SiteConfig          — dataclass, pass to any builder
    DEFAULT_CONFIG      — sensible default instance

Utilities (importable individually):
    generate_htmls.urls
    generate_htmls.text
    generate_htmls.fileio
    generate_htmls.meta
"""

from .config import SiteConfig, DEFAULT_CONFIG
from .pages import get_viewer_page, get_image_page, get_gallery_page
from .builder import build_standalone_page
from .renderer import render_to_file
