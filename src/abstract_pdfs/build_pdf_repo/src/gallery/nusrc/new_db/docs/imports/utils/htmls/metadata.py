from dataclasses import dataclass, field
from typing import Optional
import json
import html as html_lib

from .imports import *
# ─── Config ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SiteConfig:
    domain: str = DOMAIN
    url: str = ROOT_URL
    creator: str = SITE_NAME
    author: str = f"@{SITE_NAME}"
    twitter_site: str = f"@{SITE_NAME}"
    theme_color: str = "#FFFFFF"
    color_scheme: str = "light"
    charset: str = "UTF-8"
    license: str = "CC BY-SA 4.0"


DEFAULT_SITE = SiteConfig()


# ─── Schema ───────────────────────────────────────────────────────────

@dataclass
class PageMeta:
    title: str
    description: str
    keywords: list[str]
    canonical_url: str
    image_url: str
    page_url: str
    site: SiteConfig = field(default_factory=lambda: DEFAULT_SITE)
    og_type: str = "article"
    twitter_card: str = "summary_large_image"
    robots: str = "index, follow"
    image_alt: Optional[str] = None
    locale: str = "en_US"

    def __post_init__(self):
        # kill None-as-string at the source
        self.title = self.title or ""
        self.description = (self.description or "")[:300]
        self.image_alt = self.image_alt or self.title
        if isinstance(self.keywords, str):
            self.keywords = [k.strip() for k in self.keywords.split(",") if k.strip()]

    @property
    def keywords_str(self) -> str:
        return ", ".join(self.keywords)


# ─── Single meta builder ─────────────────────────────────────────────

def _esc(val: str) -> str:
    return html_lib.escape(str(val), quote=True)


def render_meta_tags(meta: PageMeta) -> str:
    s = meta.site
    tags = [
        f'<meta charset="{s.charset}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta name="theme-color" content="{s.theme_color}">',
        f'<meta name="color-scheme" content="{s.color_scheme}">',
        f"<title>{_esc(meta.title)} | {s.domain}</title>",
        f'<meta name="description" content="{_esc(meta.description)}">',
        f'<meta name="keywords" content="{_esc(meta.keywords_str)}">',
        f'<meta name="robots" content="{meta.robots}">',
        f'<meta name="author" content="{_esc(s.author)}">',
        # og
        f'<meta property="og:type" content="{meta.og_type}">',
        f'<meta property="og:title" content="{_esc(meta.title)}">',
        f'<meta property="og:description" content="{_esc(meta.description)}">',
        f'<meta property="og:url" content="{_esc(meta.page_url)}">',
        f'<meta property="og:image" content="{_esc(meta.image_url)}">',
        f'<meta property="og:image:alt" content="{_esc(meta.image_alt)}">',
        f'<meta property="og:site_name" content="{_esc(s.domain)}">',
        f'<meta property="og:locale" content="{meta.locale}">',
        # twitter
        f'<meta name="twitter:card" content="{meta.twitter_card}">',
        f'<meta name="twitter:title" content="{_esc(meta.title)}">',
        f'<meta name="twitter:description" content="{_esc(meta.description)}">',
        f'<meta name="twitter:image" content="{_esc(meta.image_url)}">',
        f'<meta name="twitter:site" content="{_esc(s.twitter_site)}">',
        f'<meta name="twitter:creator" content="{_esc(s.creator)}">',
        # canonical
        f'<link rel="canonical" href="{_esc(meta.canonical_url)}">',
    ]
    return "\n  ".join(tags)


def render_schema_ld(meta: PageMeta, schema_type: str = "CreativeWork", **extra) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": meta.title,
        "description": meta.description,
        "keywords": meta.keywords_str,
        "url": meta.canonical_url,
        "thumbnailUrl": meta.image_url,
        **extra,
    }
    return f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'



# ─── Factory: build PageMeta from the data dicts you already have ─────

def build_page_meta(
    *,
    title: str,
    description: str,
    keywords: list[str],
    image_path: str,
    page_path: str,
    canonical_path: Optional[str] = None,
    image_alt: Optional[str] = None,
    og_type: str = "article",
    site: SiteConfig = DEFAULT_SITE,
) -> PageMeta:
    image_url = path_to_url(image_path)
    page_url = path_to_url(page_path)
    canonical_url = path_to_url(canonical_path or page_path)

    return PageMeta(
        title=title,
        description=description,
        keywords=keywords,
        canonical_url=canonical_url,
        image_url=image_url,
        page_url=page_url,
        image_alt=image_alt,
        og_type=og_type,
        site=site,
    )
