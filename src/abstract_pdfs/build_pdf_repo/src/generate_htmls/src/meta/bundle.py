"""
Meta-bundle construction.

Takes raw metadata (as read from metadata.json) and resolves every field
into a complete OG / Twitter / other dict ready for Jinja2 templates.

No I/O — pure data transformation.
"""
from __future__ import annotations

from ..urls import ensure_public_url, path_to_url
from ..config import DEFAULT_CONFIG


def _resolve_canonical(source_dir, metadata, fallback_url, cfg=None):
    """Pick the best canonical URL from metadata, falling back to path_to_url."""
    cfg = cfg or DEFAULT_CONFIG
    canonical = str(metadata.get("canonical") or "").strip()
    if canonical.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf")):
        return path_to_url(source_dir, cfg.media_root, cfg.root_url) if source_dir else fallback_url
    if canonical:
        return ensure_public_url(canonical, cfg.media_root, cfg.root_url)
    if source_dir:
        return path_to_url(source_dir, cfg.media_root, cfg.root_url)
    return fallback_url


def _pick_thumbnail(metadata, first_thumb="", cfg=None):
    """Walk the thumbnail priority chain, return first public URL found."""
    cfg = cfg or DEFAULT_CONFIG
    og = metadata.get("og") or {}
    twitter = metadata.get("twitter") or {}
    _eu = lambda v: ensure_public_url(v, cfg.media_root, cfg.root_url)

    for candidate in [
        metadata.get("thumbnail_link"),
        metadata.get("thumbnail_url_resized"),
        metadata.get("thumbnail_resized"),
        metadata.get("thumbnail"),
        og.get("image"),
        twitter.get("image"),
    ]:
        resolved = _eu(candidate)
        if resolved:
            return resolved
    return first_thumb


def build_meta_bundle(
    *,
    metadata,
    title,
    description,
    canonical_url,
    first_thumb="",
    keywords_list=None,
    cfg=None,
):
    """
    Build the fully-resolved meta dict consumed by viewer / image templates.

    Returns::

        {
            "thumbnail_url": str,
            "published_time": str,
            "modified_time": str,
            "og": { ... },
            "twitter": { ... },
            "other": { ... },
        }
    """
    cfg = cfg or DEFAULT_CONFIG
    keywords_list = keywords_list or []
    og = metadata.get("og") or {}
    twitter = metadata.get("twitter") or {}
    other = metadata.get("other") or {}

    published_time = (
        ((og.get("article") or {}).get("published_time"))
        or metadata.get("published_time")
        or ""
    )
    modified_time = (
        ((og.get("article") or {}).get("modified_time"))
        or og.get("updated_time")
        or metadata.get("modified_time")
        or ""
    )

    thumbnail_url = _pick_thumbnail(metadata, first_thumb, cfg)

    source_dir = metadata.get("source_dir", "")
    og_url = (
        _resolve_canonical(source_dir, metadata, canonical_url, cfg)
        if source_dir
        else canonical_url
    )

    resolved_og = {
        "type":         og.get("type") or "article",
        "title":        og.get("title") or title,
        "description":  og.get("description") or description,
        "url":          og_url,
        "image":        thumbnail_url,
        "image_alt":    og.get("image_alt") or title,
        "image_width":  og.get("image_width") or "",
        "image_height": og.get("image_height") or "",
        "image_type":   og.get("image_type") or "",
        "locale":       og.get("locale") or "en_US",
        "site_name":    og.get("site_name") or cfg.site_name,
        "article": {
            "published_time": published_time,
            "modified_time":  modified_time,
            "section":        ((og.get("article") or {}).get("section")) or "",
            "tag":            ((og.get("article") or {}).get("tag")) or keywords_list,
        },
    }

    twitter_card = twitter.get("card") or "summary_large_image"
    if twitter_card == "app":
        twitter_card = "summary_large_image"

    site_handle = "@{}".format(cfg.site_name)
    resolved_twitter = {
        "card":        twitter_card,
        "title":       twitter.get("title") or title,
        "description": twitter.get("description") or description,
        "site":        twitter.get("site") or site_handle,
        "creator":     twitter.get("creator") or site_handle,
        "image":       thumbnail_url,
        "image_alt":   twitter.get("image_alt") or title,
        "domain":      twitter.get("domain") or cfg.domain,
    }

    resolved_other = {
        "robots":      other.get("robots") or "index, follow",
        "googlebot":   other.get("googlebot") or "index, follow",
        "author":      other.get("author") or site_handle,
        "viewport":    other.get("viewport") or "width=device-width, initial-scale=1",
        "theme_color": other.get("theme_color") or "#FFFFFF",
        "referrer":    other.get("referrer") or "origin-when-cross-origin",
    }

    return {
        "thumbnail_url":  thumbnail_url,
        "published_time": published_time,
        "modified_time":  modified_time,
        "og":             resolved_og,
        "twitter":        resolved_twitter,
        "other":          resolved_other,
    }


def build_schema(
    *,
    metadata,
    title,
    description,
    canonical_url,
    meta_bundle,
    keywords_list=None,
    schema_type="ScholarlyArticle",
):
    """
    Build JSON-LD schema dict.  Uses existing metadata.schema if present,
    otherwise constructs a default.
    """
    existing = metadata.get("schema")
    if existing:
        return existing

    return {
        "@context":     "https://schema.org",
        "@type":        schema_type,
        "name":         title,
        "headline":     title,
        "description":  description,
        "url":          canonical_url,
        "thumbnailUrl": meta_bundle.get("thumbnail_url", ""),
        "image":        meta_bundle.get("thumbnail_url", ""),
        "fileFormat":   "application/pdf",
        "datePublished": meta_bundle.get("published_time", ""),
        "dateModified":  meta_bundle.get("modified_time", ""),
        "keywords":     keywords_list or [],
    }
