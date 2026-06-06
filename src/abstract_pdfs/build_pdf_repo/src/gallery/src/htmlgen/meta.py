import json


def esc(val):
    if val is None:
        return ""
    return str(val).replace('"', "&quot;")


def tag(name, content):
    if not content:
        return ""
    return f'<meta name="{name}" content="{esc(content)}">'


def prop(name, content):
    if not content:
        return ""
    return f'<meta property="{name}" content="{esc(content)}">'


def build_meta(meta: dict) -> str:
    lines = []

    title = meta.get("title")
    description = meta.get("description")
    keywords = meta.get("keywords")
    canonical = meta.get("canonical")
    image = meta.get("thumbnail_link") or meta.get("og", {}).get("image")

    # BASIC
    if title:
        lines.append(f"<title>{esc(title)}</title>")

    lines.append(tag("description", description))
    lines.append(tag("keywords", keywords))

    # canonical + favicon
    if canonical:
        lines.append(f'<link rel="canonical" href="{esc(canonical)}">')

    if image:
        lines.append(f'<link rel="icon" href="{esc(image)}">')

    # OG
    og = meta.get("og", {})
    lines.append(prop("og:title", og.get("title") or title))
    lines.append(prop("og:description", og.get("description") or description))
    lines.append(prop("og:url", og.get("url") or canonical))
    lines.append(prop("og:image", og.get("image") or image))
    lines.append(prop("og:type", og.get("type", "article")))

    # ARTICLE
    article = og.get("article", {})
    if article.get("published_time"):
        lines.append(prop("article:published_time", article["published_time"]))

    for t in article.get("tag", []):
        lines.append(prop("article:tag", t))

    # TWITTER
    twitter = meta.get("twitter", {})
    lines.append(tag("twitter:card", "summary_large_image"))
    lines.append(tag("twitter:title", twitter.get("title") or title))
    lines.append(tag("twitter:description", twitter.get("description") or description))
    lines.append(tag("twitter:image", twitter.get("image") or image))

    # STRUCTURED DATA
    structured = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "image": image,
    }

    lines.append(
        '<script type="application/ld+json">' +
        json.dumps(structured) +
        '</script>'
    )

    return "\n".join([l for l in lines if l])
