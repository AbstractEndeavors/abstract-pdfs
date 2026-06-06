"""
URL / path resolution.

Every function takes explicit media_root and site_root — no hidden globals.
One copy of each conversion, used everywhere.
"""
from __future__ import annotations
import os

from .config import DEFAULT_CONFIG


def path_to_url(path, media_root=None, site_root=None):
    """Local filesystem path  →  public URL."""
    media_root = media_root or DEFAULT_CONFIG.media_root
    site_root = site_root or DEFAULT_CONFIG.root_url
    rel = os.path.realpath(path).replace(os.path.realpath(media_root), "").lstrip(os.sep)
    return "{}/{}".format(site_root, rel.replace(os.sep, "/"))


def url_to_path(url, media_root=None, site_root=None):
    """Public URL  →  local filesystem path (or None if url is foreign)."""
    site_root = site_root or DEFAULT_CONFIG.root_url
    media_root = media_root or DEFAULT_CONFIG.media_root
    if not url or site_root not in url:
        return None
    rel = url.replace(site_root, "").lstrip("/")
    return os.path.join(media_root, rel)


def ensure_public_url(value, media_root=None, site_root=None):
    """
    Coerce a value that might be an absolute local path, a relative path,
    or already a URL into a guaranteed public URL.  Returns '' for falsy input.
    """
    if not value:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    media_root = media_root or DEFAULT_CONFIG.media_root
    site_root = site_root or DEFAULT_CONFIG.root_url
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/"):
        if os.path.exists(value):
            return path_to_url(value, media_root=media_root, site_root=site_root)
        return "{}/{}".format(site_root.rstrip("/"), value.lstrip("/"))
    return value


def find_correct_path(broken_path, media_root=None):
    """
    Given a broken expected path, try to locate the same filename
    somewhere under media_root.  Prefer a match whose parent dir
    name also matches.
    """
    media_root = media_root or DEFAULT_CONFIG.media_root
    target = os.path.basename(broken_path)
    if not target:
        return None
    # walk once, collect matches
    matches = []
    for dirpath, _dirs, filenames in os.walk(media_root):
        if target in filenames:
            matches.append(os.path.join(dirpath, target))
    if len(matches) == 1:
        return matches[0]
    parent_name = os.path.basename(os.path.dirname(broken_path))
    for m in matches:
        if os.path.basename(os.path.dirname(m)) == parent_name:
            return m
    return None


def verified_url(url, media_root=None, site_root=None):
    """Return url if the backing file exists, else try find_correct_path."""
    if not url:
        return None
    media_root = media_root or DEFAULT_CONFIG.media_root
    site_root = site_root or DEFAULT_CONFIG.root_url
    expected = url_to_path(url, media_root, site_root)
    if expected is None:
        return url
    if os.path.exists(expected):
        return url
    correct = find_correct_path(expected, media_root)
    return path_to_url(correct, media_root, site_root) if correct else None


def rel_path(path, root):
    """Strip root prefix from path, returning relative remainder."""
    if root and root in str(path):
        return str(path).replace(root, "").lstrip("/")
    return None
