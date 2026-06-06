"""
File I/O helpers and filesystem utilities.

Wraps the abstract_utilities read/write so the rest of the codebase
never has to repeat the 'if os.path.isfile(...) else {}' pattern.
"""
from __future__ import annotations
import json
import os
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe read / write
# ---------------------------------------------------------------------------

def safe_read_json(file_path):
    """Read JSON file → dict.  Returns {} on missing/corrupt."""
    if not file_path or not os.path.isfile(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if data else {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("bad json %s: %s", file_path, exc)
        return {}


def safe_read_text(file_path):
    """Read text file → str.  Returns '' on missing."""
    if not file_path or not os.path.isfile(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        logger.warning("read failed %s: %s", file_path, exc)
        return ""


def safe_write_json(file_path, data):
    """Write data as JSON, creating parent dirs as needed."""
    if not file_path or data is None:
        return
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def safe_write_text(file_path, contents):
    """Write text, creating parent dirs as needed."""
    if not file_path:
        return
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(contents or "")


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_manifest(directory):
    """
    Try <dirname>_manifest.json then manifest.json.
    Returns the parsed list or None.
    """
    dirbase = os.path.basename(directory)
    for name in ["{}_manifest.json".format(dirbase), "manifest.json"]:
        path = os.path.join(directory, name)
        data = safe_read_json(path)
        if isinstance(data, list) and data:
            return data
    return None


# ---------------------------------------------------------------------------
# Image discovery
# ---------------------------------------------------------------------------

def find_image_candidate(page_dir, extra_candidates=None):
    """
    Look for the first existing image file in page_dir.
    Returns the absolute path or None.
    """
    defaults = ["image.webp", "image.png", "image.jpg", "image.jpeg"]
    candidates = list(extra_candidates or []) + defaults
    for name in candidates:
        full = os.path.join(page_dir, name)
        if os.path.isfile(full):
            return full
    return None


def first_real_image(directory, exts=None):
    """
    Recursively find the first image file under directory.
    Returns absolute path or None.
    """
    exts = exts or [".png", ".jpg", ".jpeg", ".webp", ".gif"]
    for dirpath, _dirs, filenames in os.walk(directory):
        for fname in sorted(filenames):
            if any(fname.lower().endswith(ext) for ext in exts):
                return os.path.join(dirpath, fname)
    return None


# ---------------------------------------------------------------------------
# Child directory listing
# ---------------------------------------------------------------------------

def child_dirs(directory, skip=None):
    """Sorted list of visible child directories, skipping known junk."""
    skip = skip or frozenset()
    if not os.path.isdir(directory):
        return []
    entries = []
    for name in sorted(os.listdir(directory)):
        full = os.path.join(directory, name)
        if os.path.isdir(full) and name not in skip and not name.startswith("."):
            entries.append(full)
    return entries


# ---------------------------------------------------------------------------
# Breadcrumbs
# ---------------------------------------------------------------------------

def build_breadcrumbs(base_url, site_root):
    """
    Produce HTML breadcrumb string from a full URL.
    'https://site.com/a/b/c' → 'Home › A › B › c'
    """
    from .text import humanize  # local to avoid circular

    path_part = base_url.rstrip("/").replace(site_root, "").lstrip("/")
    segments = [s for s in path_part.split("/") if s]
    crumbs = ['<a href="{}">Home</a>'.format(site_root)]
    acc = site_root
    for i, seg in enumerate(segments):
        acc += "/{}".format(seg)
        if i < len(segments) - 1:
            crumbs.append('<a href="{}/">{}</a>'.format(acc, humanize(seg)))
        else:
            crumbs.append("<span>{}</span>".format(seg))
    return " › ".join(crumbs)
