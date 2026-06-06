"""
Jinja2 environment factory.

Templates live in the `templates/` subdirectory of this package.
"""
from __future__ import annotations
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

_env = None


def get_jinja_env(extra_dirs=None):
    """
    Return a cached Jinja2 Environment.

    extra_dirs – additional search paths prepended to the loader
    (useful if your project has templates outside this package).
    """
    global _env
    if _env is not None and not extra_dirs:
        return _env

    search_dirs = list(extra_dirs or []) + [_TEMPLATE_DIR]
    env = Environment(
        loader=FileSystemLoader(search_dirs),
        autoescape=select_autoescape(["html", "xml"]),
    )
    if not extra_dirs:
        _env = env
    return env
