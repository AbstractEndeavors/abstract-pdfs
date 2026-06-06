"""
Site-wide configuration.

One dataclass, explicit fields, no module-level side effects.
Consumers receive a SiteConfig instance — they never reach into globals.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Image extensions — inlined so config.py has zero exotic deps
# ---------------------------------------------------------------------------
IMAGE_EXTS = [
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".bmp", ".tiff", ".tif", ".svg", ".ico",
]

SKIP_DIRS = frozenset({
    "text", "pages", "images", "thumbnails", "pdf_pages",
    "preprocessed_images", "preprocessed_text",
    "node_modules", ".git", "__pycache__",
})

IMAGE_CANDIDATES = ["image.webp", "image.png", "image.jpg", "image.jpeg"]


@dataclass(frozen=True)
class SiteConfig:
    """Immutable bag of every path / URL the pipeline needs."""

    site_name:   str = "thedailydialectics"
    domain:      str = "thedailydialectics.com"
    root_url:    str = "https://thedailydialectics.com"

    # derived URL prefixes
    imgs_url:    str = ""
    pdfs_url:    str = ""

    # local filesystem roots
    root_dir:    str = "/var/www/presites/thedailydialectics/react/main"
    media_root:  str = "/srv/media/thedailydialectics"

    # sub-dirs (computed in __post_init__)
    imgs_dir:    str = ""
    pdfs_dir:    str = ""
    pages_dir:   str = ""
    media_pages_dir: str = ""

    image_exts:  tuple = tuple(IMAGE_EXTS)
    skip_dirs:   frozenset = SKIP_DIRS

    def __post_init__(self):
        # frozen=True requires object.__setattr__ for computed fields
        _set = object.__setattr__
        _set(self, "imgs_url",  f"{self.root_url}/imgs")
        _set(self, "pdfs_url",  f"{self.root_url}/pdfs")
        _set(self, "imgs_dir",  os.path.join(self.media_root, "imgs"))
        _set(self, "pdfs_dir",  os.path.join(self.media_root, "pdfs"))
        _set(self, "pages_dir", os.path.join(self.root_dir, "pages"))
        _set(self, "media_pages_dir", os.path.join(self.media_root, "pages"))


# ---------------------------------------------------------------------------
# Default instance — importable, but never mutated
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = SiteConfig()
