from __future__ import annotations

from jinja2 import Environment, FileSystemLoader
import os

SRC_ROOT = "/var/www/ABSTRACT_ENDEAVORS/scripts/python/generat_htmls/src"

def get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(SRC_ROOT),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
