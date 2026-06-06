"""
SEO meta-tag HTML generation.

Produces the <meta>, <title>, <link>, and <script type=ld+json> block
that goes inside <head>.  Used by the standalone HTML builder (template.py)
and can also feed the gallery template.
"""
from __future__ import annotations
import json


def _esc(val):
    if val is None:
        return ""
    return str(val).replace('"', "&quot;")


def _tag(name, content):
    if not content:
        return ""
    return '<meta name="{}" content="{}">'.format(name, _esc(content))


def _prop(name, content):
    if not content:
        return ""
    return '<meta property="{}" content="{}">'.format(name, _esc(content))


def build_seo_html(meta):
    """
    Accept a flat meta dict (title, description, keywords, canonical,
    thumbnail_link, og, twitter) and return the full <head> inner HTML.
    """
    lines = []

    title       = meta.get("title")
    description = meta.get("description")
    keywords    = meta.get("keywords")
    canonical   = meta.get("canonical")
    image       = meta.get("thumbnail_link") or (meta.get("og") or {}).get("image")

    # --- basic ---
    if title:
        lines.append("<title>{}</title>".format(_esc(title)))
    lines.append(_tag("description", description))
    lines.append(_tag("keywords", keywords))

    if canonical:
        lines.append('<link rel="canonical" href="{}">'.format(_esc(canonical)))
    if image:
        lines.append('<link rel="icon" href="{}">'.format(_esc(image)))

    # --- OG ---
    og = meta.get("og") or {}
    lines.append(_prop("og:title",       og.get("title") or title))
    lines.append(_prop("og:description", og.get("description") or description))
    lines.append(_prop("og:url",         og.get("url") or canonical))
    lines.append(_prop("og:image",       og.get("image") or image))
    lines.append(_prop("og:type",        og.get("type", "article")))

    article = og.get("article") or {}
    if article.get("published_time"):
        lines.append(_prop("article:published_time", article["published_time"]))
    for t in (article.get("tag") or []):
        lines.append(_prop("article:tag", t))

    # --- Twitter ---
    twitter = meta.get("twitter") or {}
    lines.append(_tag("twitter:card",        "summary_large_image"))
    lines.append(_tag("twitter:title",       twitter.get("title") or title))
    lines.append(_tag("twitter:description", twitter.get("description") or description))
    lines.append(_tag("twitter:image",       twitter.get("image") or image))

    # --- JSON-LD ---
    structured = {
        "@context":    "https://schema.org",
        "@type":       "Article",
        "headline":    title,
        "description": description,
        "image":       image,
    }
    lines.append(
        '<script type="application/ld+json">'
        + json.dumps(structured, ensure_ascii=False)
        + "</script>"
    )

    return "\n".join(line for line in lines if line)
