"""
Text manipulation utilities.

Pure functions, no I/O, no config dependency.
"""
from __future__ import annotations
import re


def humanize(name):
    """'some-slug_thing' → 'Some Slug Thing'"""
    return name.replace("-", " ").replace("_", " ").title()


def slugify(text):
    """'Some Title / Thing' → 'some-title---thing' (minimal, url-safe)"""
    return text.lower().replace(" ", "-").replace("/", "-")


def clean_text(value, max_len=180):
    """
    Collapse whitespace, handle list-of-strings, truncate with ellipsis.
    """
    if isinstance(value, list):
        value = str(value[0]) if value else ""
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    if len(value) <= max_len:
        return value
    return value[:max_len].rsplit(" ", 1)[0] + "…"


def dedupe_keywords(values, limit=20):
    """Deduplicate keyword list (case-insensitive), capped at limit."""
    seen = set()
    out = []
    for raw in values:
        kw = str(raw or "").strip()
        key = kw.lower()
        if not kw or key in seen:
            continue
        seen.add(key)
        out.append(kw)
        if len(out) >= limit:
            break
    return out


def normalize_keyword_input(raw):
    """
    Accept str, list, or None → always return a list of stripped strings.
    """
    if not raw:
        return []
    if isinstance(raw, str):
        return [k.strip() for k in raw.split(",") if k.strip()]
    if isinstance(raw, list):
        return [str(k).strip() for k in raw if str(k).strip()]
    return []


def normalize_keywords(metadata, extra_keywords=None, limit=20):
    """
    Merge keywords from a metadata dict with an optional extra list,
    deduplicated, capped.
    """
    base = normalize_keyword_input(metadata.get("keywords"))
    extra = list(extra_keywords or [])
    return dedupe_keywords(base + extra, limit=limit)


def extract_description(manifest, max_len=160):
    """
    Best available description from a page manifest entry.
    Priority: longdesc → caption → keywords_str
    """
    if not manifest:
        return ""
    first = manifest[0] if isinstance(manifest, list) else manifest
    raw = (
        first.get("longdesc")
        or first.get("caption")
        or first.get("keywords_str", "").replace(",", " ")
        or ""
    )
    return clean_text(raw, max_len)


def extract_keywords_from_manifest(manifest, limit=8):
    """Aggregate keywords across all manifest pages, deduped, capped."""
    if not manifest or not isinstance(manifest, list):
        return []
    all_kw = []
    for entry in manifest:
        raw = entry.get("keywords_str", "")
        all_kw.extend(k.strip() for k in raw.split(",") if k.strip())
    return dedupe_keywords(all_kw, limit=limit)


def zero_pad(i, width=3):
    """Zero-pad an integer to `width` chars: zero_pad(7) → '007'"""
    return str(i).zfill(width)
