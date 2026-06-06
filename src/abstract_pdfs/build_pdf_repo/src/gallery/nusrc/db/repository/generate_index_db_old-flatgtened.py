#!/usr/bin/env python3
"""
generate_index_db.py — Static HTML generation from the document registry DB.

Same output as generate_index_html.py (viewer pages + gallery indexes),
but reads from the database instead of walking filesystem manifests.

The filesystem is still the blob store (images, text files). The DB is the
registry that tells us what exists and how to describe it.

Design:
  - Repository + SeoRepository are injected, never created internally.
  - Intermediate shapes are dataclasses, never raw dicts from queries.
  - Path→URL conversion is explicit and deterministic.
  - No module-level state. Wire everything at the CLI entry point.

Usage:
    python generate_index_db.py \\
        --dsn          "postgresql://user:pass@localhost:5432/tdd_docs" \\
        --tenant-slug  default \\
        --output-root  /srv/media/thedailydialectics/pdfs \\
        --media-root   /srv/media/thedailydialectics \\
        --site-root    https://thedailydialectics.com \\
        --url-prefix   /pdfs

    # Single document:
    python generate_index_db.py \\
        --dsn          "postgresql://user:pass@localhost:5432/tdd_docs" \\
        --tenant-slug  default \\
        --output-root  /srv/media/thedailydialectics/pdfs \\
        --media-root   /srv/media/thedailydialectics \\
        --site-root    https://thedailydialectics.com \\
        --url-prefix   /pdfs \\
        --slug         a197278 \\
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


# ── Import your existing repos ──────────────────────────────
# Adjust these imports to match your package layout.
# If running from the same directory as repository.py:
from repository import Repository, Status
from repository_seo import SeoRepository, DocumentSeo


# ═══════════════════════════════════════════════════════════════
# Intermediate shapes — what we need to render, nothing more
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class PageView:
    """One page's worth of rendering data."""
    page_number: int
    image_url: str | None      # absolute URL to thumbnail/image
    text: str                  # extracted text content (for search)
    alt: str                   # alt text
    image_path: str | None     # filesystem path (for existence checks)
    text_path: str | None      # filesystem path to text file


@dataclass(frozen=True, slots=True)
class DocumentView:
    """Everything needed to render a viewer page for one document."""
    document_id: int
    slug: str
    title: str
    description: str
    keywords: str
    pdf_url: str
    thumbnail_url: str | None
    canonical_url: str | None
    og: dict[str, Any]
    tags: list[str]
    pages: list[PageView]
    base_path: str             # filesystem root for this document


@dataclass(frozen=True, slots=True)
class GalleryCard:
    """One card in a gallery index."""
    slug: str
    title: str
    description: str
    image_url: str | None
    href: str
    tags: list[str]
    page_count: int | None
    status: str


# ═══════════════════════════════════════════════════════════════
# Path ↔ URL conversion
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class PathResolver:
    """
    Deterministic conversion between filesystem paths and public URLs.
    No guessing — media_root and site_root are explicit.
    """
    media_root: Path
    site_root: str      # e.g. "https://thedailydialectics.com"

    def path_to_url(self, path: str | Path) -> str | None:
        """Convert an absolute filesystem path to a public URL."""
        p = Path(path)
        if not p.is_absolute():
            return None
        try:
            rel = p.relative_to(self.media_root)
            return f"{self.site_root}/{rel}"
        except ValueError:
            return None

    def url_exists(self, path: str | Path | None) -> str | None:
        """Return URL only if the file actually exists on disk."""
        if path is None:
            return None
        p = Path(path)
        if p.exists():
            return self.path_to_url(p)
        return None


# ═══════════════════════════════════════════════════════════════
# Data assembly — DB reads into intermediate shapes
# ═══════════════════════════════════════════════════════════════


def _read_text_file(path: str | None) -> str:
    """Read text content from disk. Returns empty string on any failure."""
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def assemble_document_view(
    repo: Repository,
    seo_repo: SeoRepository,
    document_id: int,
    resolver: PathResolver,
    url_prefix: str,
) -> DocumentView | None:
    """
    Pull everything for one document from the DB and assemble a DocumentView.
    Returns None if the document or its SEO record doesn't exist.
    """
    doc = repo.get_document(document_id)
    if doc is None:
        return None

    seo: DocumentSeo | None = seo_repo.get_seo(document_id)
    if seo is None:
        # No SEO record → can't render a meaningful page
        return None

    # Pages from the DB
    db_pages = repo.get_pages(document_id)

    # Page-level meta_info payloads (alt, caption, longdesc, etc.)
    page_metas = seo_repo.get_all_page_metas(document_id)
    meta_by_index = {i: m for i, m in enumerate(page_metas)}

    # Tags
    db_tags = repo.get_document_tags(document_id)
    tag_labels = [t.label for t in db_tags]

    # Assemble page views
    pages: list[PageView] = []
    for i, pg in enumerate(db_pages):
        meta = meta_by_index.get(i, {}) or {}

        # Image URL: page's image_path → public URL
        image_url = resolver.url_exists(pg.image_path)

        # Text: read from text_path on disk, fall back to meta longdesc
        text = _read_text_file(pg.text_path)
        if not text:
            text = meta.get("longdesc", "") or meta.get("text", "")

        # Alt text: from meta, or synthesized
        alt = (
            meta.get("alt")
            or meta.get("title")
            or f"{seo.title} — Page {pg.page_number}"
        )

        pages.append(PageView(
            page_number=pg.page_number,
            image_url=image_url,
            text=text,
            alt=alt,
            image_path=pg.image_path,
            text_path=pg.text_path,
        ))

    # PDF URL
    pdf_url = resolver.path_to_url(doc.pdf_path) or doc.pdf_path

    # Thumbnail: SEO record → first page image fallback
    thumbnail = seo.thumbnail_url
    if not thumbnail and pages:
        thumbnail = pages[0].image_url

    return DocumentView(
        document_id=doc.id,
        slug=doc.slug,
        title=seo.title,
        description=seo.description,
        keywords=seo.keywords,
        pdf_url=pdf_url,
        thumbnail_url=thumbnail,
        canonical_url=seo.canonical_url,
        og=seo.og,
        tags=tag_labels,
        pages=pages,
        base_path=doc.base_path,
    )


def assemble_gallery(
    repo: Repository,
    seo_repo: SeoRepository,
    tenant_id: str,
    resolver: PathResolver,
    url_prefix: str,
    status_filter: Status | None = None,
) -> list[GalleryCard]:
    """
    Build gallery cards for all documents belonging to a tenant.
    Only includes documents that have a SEO record.
    """
    docs = repo.list_documents(tenant_id, status=status_filter, limit=10000)
    cards: list[GalleryCard] = []

    for doc in docs:
        seo = seo_repo.get_seo(doc.id)
        if seo is None:
            continue

        # Thumbnail: SEO thumbnail_url → first page image → None
        thumb_url = seo.thumbnail_url
        if not thumb_url:
            pages = repo.get_pages(doc.id)
            if pages and pages[0].image_path:
                thumb_url = resolver.url_exists(pages[0].image_path)

        tags = [t.label for t in repo.get_document_tags(doc.id)]

        cards.append(GalleryCard(
            slug=doc.slug,
            title=seo.title,
            description=_clean_text(seo.description, 160),
            image_url=thumb_url,
            href=f"{url_prefix.rstrip('/')}/{doc.slug}/",
            tags=tags,
            page_count=doc.page_count,
            status=doc.status.value,
        ))

    return cards


# ═══════════════════════════════════════════════════════════════
# Text helpers (same logic as your v5 script)
# ═══════════════════════════════════════════════════════════════

SITE_ROOT_DEFAULT = "https://thedailydialectics.com"


def _clean_text(s: str | list, max_len: int = 160) -> str:
    if isinstance(s, list):
        s = str(s[0]) if s else ""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0] + "…"
    return s


def _humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


def _esc_html_attr(s: str) -> str:
    """Escape for use inside HTML attribute values."""
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _breadcrumbs(url: str, site_root: str) -> str:
    path_part = url.rstrip("/").replace(site_root, "").lstrip("/")
    segments = [s for s in path_part.split("/") if s]
    crumbs = [f'<a href="{site_root}">Home</a>']
    acc = site_root
    for i, seg in enumerate(segments):
        acc += f"/{seg}"
        if i < len(segments) - 1:
            crumbs.append(f'<a href="{acc}/">{_humanize(seg)}</a>')
        else:
            crumbs.append(f"<span>{seg}</span>")
    return " › ".join(crumbs)


# ═══════════════════════════════════════════════════════════════
# HTML renderers — same templates as v5, fed by DocumentView
# ═══════════════════════════════════════════════════════════════


def render_viewer_page(view: DocumentView, site_root: str) -> str:
    """Render a PDF viewer page from a DocumentView."""
    total = len(view.pages)
    canonical = view.canonical_url or f"{site_root}/pdfs/{view.slug}/"

    pages_js = []
    for pv in view.pages:
        pages_js.append({
            "n": pv.page_number,
            "thumb": pv.image_url or "",
            "text": pv.text,
            "alt": pv.alt.split(" | ")[0] if pv.alt else f"Page {pv.page_number}",
        })

    pages_json = json.dumps(pages_js, ensure_ascii=False)

    keywords_list = [
        kw.strip()
        for kw in view.keywords.split(",")
        if kw.strip() and len(kw.strip()) > 2
    ][:12]

    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": view.title,
        "description": _clean_text(view.description, 300),
        "keywords": view.keywords,
        "url": view.pdf_url,
        "thumbnailUrl": view.thumbnail_url or "",
        "fileFormat": "application/pdf",
    }

    first_thumb = pages_js[0]["thumb"] if pages_js else ""
    desc_escaped = _esc_html_attr(_clean_text(view.description, 300))
    title_escaped = _esc_html_attr(view.title)
    kw_escaped = _esc_html_attr(view.keywords)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_escaped} | thedailydialectics</title>
  <meta name="description" content="{desc_escaped}">
  <meta name="keywords" content="{kw_escaped}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{title_escaped}">
  <meta property="og:description" content="{desc_escaped}">
  <meta property="og:image" content="{first_thumb}">
  <script type="application/ld+json">{json.dumps(schema, indent=2)}</script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0d0d0d; --surface: #1a1a1a; --surface2: #222;
      --text: #e0e0e0; --muted: #888; --accent: #7aaeff;
      --thumb-w: 110px;
    }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
            display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
    .topbar {{ display: flex; align-items: center; gap: .6rem; padding: .5rem .8rem;
               background: var(--surface); border-bottom: 1px solid #333; flex-shrink: 0; flex-wrap: wrap; }}
    .topbar a.home {{ color: var(--muted); font-size: .8rem; text-decoration: none; white-space: nowrap; }}
    .topbar a.home:hover {{ color: var(--text); }}
    .topbar h1 {{ font-size: .95rem; font-weight: 600; flex: 1; min-width: 0;
                  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .fmt-btns {{ display: flex; gap: .3rem; }}
    .fmt-btn {{ background: var(--surface2); border: 1px solid #444; color: var(--muted);
                padding: .25rem .6rem; border-radius: 4px; cursor: pointer; font-size: .8rem; }}
    .fmt-btn.active {{ background: var(--accent); color: #000; border-color: var(--accent); }}
    .search-wrap {{ display: flex; align-items: center; gap: .3rem; }}
    #search-input {{ background: var(--surface2); border: 1px solid #444; color: var(--text);
                     padding: .25rem .5rem; border-radius: 4px; font-size: .8rem; width: 160px; }}
    #search-status {{ font-size: .75rem; color: var(--muted); white-space: nowrap; }}
    .main {{ display: flex; flex: 1; overflow: hidden; }}
    .thumbs {{ width: var(--thumb-w); background: var(--surface); border-right: 1px solid #333;
               overflow-y: auto; overflow-x: hidden; flex-shrink: 0; padding: .4rem 0; }}
    .thumb-item {{ cursor: pointer; padding: .3rem; border-bottom: 1px solid #2a2a2a;
                   display: flex; flex-direction: column; align-items: center; gap: .2rem; }}
    .thumb-item:hover {{ background: #252525; }}
    .thumb-item.active {{ background: #1e2d4a; border-left: 3px solid var(--accent); }}
    .thumb-item img {{ width: 90px; height: 120px; object-fit: cover; border-radius: 2px;
                       display: block; background: #111; }}
    .thumb-item .pnum {{ font-size: .65rem; color: var(--muted); }}
    .thumb-placeholder {{ width: 90px; height: 120px; background: #222; border-radius: 2px;
                           display: flex; align-items: center; justify-content: center;
                           font-size: .7rem; color: var(--muted); }}
    .viewer {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
    .abstract-bar {{ background: #111; border-bottom: 1px solid #2a2a2a;
                     padding: .5rem 1rem; font-size: .8rem; color: #999;
                     display: flex; align-items: flex-start; gap: .6rem; flex-shrink: 0; }}
    .abstract-bar p {{ flex: 1; line-height: 1.5; }}
    .abstract-bar .tags {{ display: flex; flex-wrap: wrap; gap: .25rem; margin-top: .3rem; }}
    .abstract-bar .tag {{ background: #1e1e1e; border: 1px solid #2e2e2e; border-radius: 3px;
                           padding: .1rem .4rem; font-size: .68rem; color: #666; }}
    .abstract-toggle {{ cursor: pointer; color: var(--muted); font-size: .75rem;
                         white-space: nowrap; user-select: none; flex-shrink: 0; }}
    .abstract-toggle:hover {{ color: var(--text); }}
    .nav-bar {{ display: flex; align-items: center; gap: .5rem; padding: .4rem .7rem;
                background: var(--surface2); border-bottom: 1px solid #333; flex-shrink: 0; }}
    .nav-bar button {{ background: var(--surface); border: 1px solid #444; color: var(--text);
                       padding: .2rem .55rem; border-radius: 4px; cursor: pointer; font-size: .85rem; }}
    .nav-bar button:disabled {{ opacity: .35; cursor: default; }}
    #page-display {{ font-size: .85rem; color: var(--muted); white-space: nowrap; }}
    .content {{ flex: 1; overflow: auto; display: flex; justify-content: center; align-items: flex-start;
                padding: 1rem; }}
    #pdf-frame {{ width: 100%; height: 100%; border: none; min-height: 600px; }}
    #img-view {{ max-width: 860px; width: 100%; }}
    #img-view img {{ width: 100%; height: auto; display: block; border-radius: 4px; }}
    #txt-view {{ max-width: 860px; width: 100%; }}
    #txt-view pre {{ white-space: pre-wrap; font-size: .85rem; line-height: 1.6;
                     color: #ccc; font-family: 'Courier New', monospace; }}
    #txt-view pre mark {{ background: #7aaeff44; color: #fff; border-radius: 2px; padding: 0 2px; }}
    #hits-panel {{ max-width: 860px; width: 100%; }}
    .hit-item {{ background: var(--surface); border-radius: 6px; padding: .6rem .8rem;
                 margin-bottom: .5rem; cursor: pointer; border: 1px solid #333; }}
    .hit-item:hover {{ border-color: var(--accent); }}
    .hit-item .hit-page {{ font-size: .75rem; color: var(--accent); margin-bottom: .2rem; }}
    .hit-item .hit-snippet {{ font-size: .8rem; color: var(--muted); font-family: monospace; }}
    .hit-item .hit-snippet mark {{ background: #7aaeff44; color: #fff; }}
    @media (max-width: 600px) {{
      :root {{ --thumb-w: 70px; }}
      .thumb-item img {{ width: 60px; height: 80px; }}
      .search-wrap {{ display: none; }}
    }}
  </style>
</head>
<body>

<div class="topbar">
  <a class="home" href="{site_root}">← Home</a>
  <span style="color:#444">/</span>
  <h1>{title_escaped}</h1>
  <div class="fmt-btns">
    <button class="fmt-btn active" id="btn-pdf"    onclick="setFormat('pdf')">PDF</button>
    <button class="fmt-btn"        id="btn-images" onclick="setFormat('images')">Images</button>
    <button class="fmt-btn"        id="btn-text"   onclick="setFormat('text')">Text</button>
  </div>
  <div class="search-wrap">
    <input id="search-input" type="search" placeholder="Search text… (Ctrl+F)" autocomplete="off">
    <span id="search-status"></span>
  </div>
</div>

<div class="abstract-bar" id="abstract-bar">
  <div style="flex:1">
    <p id="abstract-text">{desc_escaped}</p>
    <div class="tags" id="kw-tags"></div>
  </div>
  <span class="abstract-toggle" onclick="toggleAbstract()">▲ hide</span>
</div>

<div class="main">
  <div class="thumbs" id="thumbs"></div>
  <div class="viewer">
    <div class="nav-bar">
      <button id="btn-first" onclick="goPage(1)" title="First">⏮</button>
      <button id="btn-prev"  onclick="goPage(cur-1)" title="Previous (←)">◀</button>
      <span id="page-display">Page 1 / {total}</span>
      <button id="btn-next"  onclick="goPage(cur+1)" title="Next (→)">▶</button>
      <button id="btn-last"  onclick="goPage({total})" title="Last">⏭</button>
      <a href="{view.pdf_url}" target="_blank" rel="noopener"
         style="margin-left:auto;font-size:.8rem;color:var(--accent);text-decoration:none">
        ⬇ Download PDF
      </a>
    </div>
    <div class="content" id="content-area">
      <iframe id="pdf-frame" src="{view.pdf_url}" title="{title_escaped}"></iframe>
    </div>
  </div>
</div>

<script>
const PAGES = {pages_json};
const PDF_URL = {json.dumps(view.pdf_url)};
const TOTAL = {total};
const KEYWORDS = {json.dumps(keywords_list)};
let cur = 1;
let fmt = 'pdf';

(function() {{
  const tags = document.getElementById('kw-tags');
  KEYWORDS.forEach(kw => {{
    const s = document.createElement('span');
    s.className = 'tag';
    s.textContent = kw;
    tags.appendChild(s);
  }});
}})();

function toggleAbstract() {{
  const bar = document.getElementById('abstract-bar');
  const btn = bar.querySelector('.abstract-toggle');
  const content = bar.querySelector('div');
  if (content.style.display === 'none') {{
    content.style.display = '';
    btn.textContent = '▲ hide';
  }} else {{
    content.style.display = 'none';
    btn.textContent = '▼ show info';
  }}
}}

function buildThumbs() {{
  const strip = document.getElementById('thumbs');
  strip.innerHTML = PAGES.map(p => `
    <div class="thumb-item ${{p.n===1?'active':''}}" id="thumb-${{p.n}}"
         onclick="goPage(${{p.n}})">
      ${{p.thumb
        ? `<img src="${{p.thumb}}" alt="${{p.alt}}" loading="lazy">`
        : `<div class="thumb-placeholder">p${{p.n}}</div>`}}
      <span class="pnum">${{p.n}}</span>
    </div>`).join('');
}}

function updateThumb(n) {{
  document.querySelectorAll('.thumb-item').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('thumb-' + n);
  if (el) {{
    el.classList.add('active');
    el.scrollIntoView({{ block: 'nearest' }});
  }}
}}

function setFormat(f) {{
  fmt = f;
  ['pdf','images','text'].forEach(id => {{
    document.getElementById('btn-'+id).classList.toggle('active', id===f);
  }});
  renderContent();
}}

function goPage(n) {{
  n = Math.max(1, Math.min(TOTAL, n));
  cur = n;
  document.getElementById('page-display').textContent = `Page ${{n}} / ${{TOTAL}}`;
  document.getElementById('btn-prev').disabled  = n <= 1;
  document.getElementById('btn-first').disabled = n <= 1;
  document.getElementById('btn-next').disabled  = n >= TOTAL;
  document.getElementById('btn-last').disabled  = n >= TOTAL;
  updateThumb(n);
  renderContent();
}}

function escHtml(s) {{
  return s.replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]));
}}

function highlight(text, q) {{
  if (!q) return '<pre>' + escHtml(text) + '</pre>';
  const rx = new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&') + ')', 'gi');
  return '<pre>' + escHtml(text).replace(rx, '<mark>$1</mark>') + '</pre>';
}}

function renderContent() {{
  const area  = document.getElementById('content-area');
  const page  = PAGES[cur - 1];
  const query = document.getElementById('search-input').value.trim();

  if (fmt === 'pdf') {{
    area.innerHTML = `<iframe id="pdf-frame" src="${{PDF_URL}}#page=${{cur}}"
                        title="PDF viewer" style="width:100%;height:100%;border:none;min-height:600px"></iframe>`;
  }} else if (fmt === 'images') {{
    area.innerHTML = page.thumb
      ? `<div id="img-view"><img src="${{page.thumb}}" alt="${{page.alt}}"></div>`
      : `<p style="color:var(--muted);padding:2rem">No image for page ${{cur}}</p>`;
  }} else if (fmt === 'text') {{
    area.innerHTML = `<div id="txt-view">${{highlight(page.text || '(no text)', query)}}</div>`;
    const mark = area.querySelector('mark');
    if (mark) mark.scrollIntoView({{ block:'center', behavior:'smooth' }});
  }}
}}

let searchTimer = null;
document.getElementById('search-input').addEventListener('input', function() {{
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => runSearch(this.value.trim()), 250);
}});

function runSearch(q) {{
  const status = document.getElementById('search-status');
  const area   = document.getElementById('content-area');
  if (!q) {{ status.textContent = ''; renderContent(); return; }}

  fmt = 'text';
  ['pdf','images','text'].forEach(id =>
    document.getElementById('btn-'+id).classList.toggle('active', id==='text'));

  const lc = q.toLowerCase();
  const hits = [];
  for (const p of PAGES) {{
    const idx = (p.text || '').toLowerCase().indexOf(lc);
    if (idx !== -1) {{
      const start = Math.max(0, idx-60);
      const end   = Math.min(p.text.length, idx+lc.length+60);
      hits.push({{ page: p.n, snippet: p.text.slice(start,end) }});
    }}
  }}

  status.textContent = hits.length ? `${{hits.length}} hit(s)` : 'no results';
  if (hits.length === 0) {{
    area.innerHTML = `<p style="color:var(--muted);padding:2rem">No results for "${{escHtml(q)}}"</p>`;
    return;
  }}

  const rx = new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&') + ')', 'gi');
  area.innerHTML = `<div id="hits-panel">` +
    hits.map(h => `
      <div class="hit-item" onclick="goPage(${{h.page}});setFormat('text')">
        <div class="hit-page">Page ${{h.page}}</div>
        <div class="hit-snippet">${{escHtml(h.snippet).replace(rx,'<mark>$1</mark>')}}</div>
      </div>`).join('') +
    `</div>`;
}}

document.addEventListener('keydown', e => {{
  if (document.activeElement === document.getElementById('search-input')) return;
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goPage(cur+1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   goPage(cur-1);
  if ((e.ctrlKey||e.metaKey) && e.key==='f') {{
    e.preventDefault();
    document.getElementById('search-input').focus();
  }}
}});

buildThumbs();
goPage(1);
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# Gallery page renderer
# ═══════════════════════════════════════════════════════════════


def render_gallery_page(
    cards: list[GalleryCard],
    title: str,
    canonical_url: str,
    site_root: str,
) -> str:
    """Render a gallery index from GalleryCard list."""

    def _card_html(c: GalleryCard) -> str:
        desc_html = ""
        if c.description:
            desc_html += f'<span class="card-desc">{_esc_html_attr(c.description)}</span>'
        if c.tags:
            tags_inner = "".join(
                f'<span class="card-tag">{t}</span>' for t in c.tags
            )
            desc_html += f'<div class="card-tags">{tags_inner}</div>'
        if c.page_count:
            desc_html += f'<span class="card-meta">{c.page_count} pages</span>'

        if c.image_url:
            return f"""        <a class="card" href="{c.href}">
          <img src="{c.image_url}" alt="{_esc_html_attr(c.title)}" loading="lazy">
          <div class="card-body">
            <span class="card-title">{_esc_html_attr(c.title)}</span>
            {desc_html}
          </div>
        </a>"""
        else:
            return f"""        <a class="card" href="{c.href}">
          <div class="card-body">
            <span class="card-title">{_esc_html_attr(c.title)}</span>
            {desc_html}
          </div>
        </a>"""

    cards_html = "\n".join(_card_html(c) for c in cards)
    bc = _breadcrumbs(canonical_url, site_root)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc_html_attr(title)} | thedailydialectics</title>
  <link rel="canonical" href="{canonical_url}">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #0d0d0d; color: #e0e0e0; padding: 2rem 1rem; }}
    nav.breadcrumb {{ font-size: .8rem; color: #888; margin-bottom: 2rem; }}
    nav.breadcrumb a {{ color: #aaa; text-decoration: none; }}
    nav.breadcrumb a:hover {{ color: #fff; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 1.5rem; color: #f0f0f0; text-transform: capitalize; }}
    .summary {{ font-size: .85rem; color: #777; margin-bottom: 1.5rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; max-width: 1200px; }}
    .card {{ background: #1a1a1a; border-radius: 8px; overflow: hidden; text-decoration: none;
             color: #e0e0e0; transition: transform .2s, box-shadow .2s; display: flex; flex-direction: column; }}
    .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.4); }}
    .card img {{ width: 100%; height: 140px; object-fit: cover; display: block; flex-shrink: 0; }}
    .card-body {{ padding: .6rem .75rem; display: flex; flex-direction: column; gap: .35rem; flex: 1; }}
    .card-title {{ font-size: .85rem; color: #ccc; text-transform: capitalize; font-weight: 600; }}
    .card-desc {{ font-size: .75rem; color: #777; line-height: 1.45;
                  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
                  overflow: hidden; }}
    .card-meta {{ font-size: .7rem; color: #555; margin-top: auto; }}
    .card-tags {{ display: flex; flex-wrap: wrap; gap: .2rem; margin-top: auto; padding-top: .3rem; }}
    .card-tag {{ background: #222; border: 1px solid #2e2e2e; border-radius: 3px;
                  padding: .1rem .35rem; font-size: .65rem; color: #666; }}
  </style>
</head>
<body>
  <nav class="breadcrumb">{bc}</nav>
  <h1>{_esc_html_attr(title)}</h1>
  <p class="summary">{len(cards)} document{"s" if len(cards) != 1 else ""} in registry</p>
  <div class="grid">
{cards_html}
  </div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# Orchestrator — wires repos to renderers, writes to disk
# ═══════════════════════════════════════════════════════════════


@dataclass
class GeneratorConfig:
    """All the explicit wiring a run needs. No smart defaults."""
    dsn: str
    tenant_slug: str
    output_root: Path
    media_root: Path
    site_root: str
    url_prefix: str           # e.g. "/pdfs" — base URL segment for documents
    slug: str | None = None   # if set, only generate for this one document
    status_filter: Status | None = None
    dry_run: bool = False


def run(config: GeneratorConfig) -> None:
    """
    Main entry point. Opens the connection, resolves the tenant,
    generates HTML, and writes to disk.
    """
    conn = psycopg.connect(config.dsn, autocommit=True)
    try:
        repo = Repository(conn)
        seo_repo = SeoRepository(conn)
        resolver = PathResolver(
            media_root=config.media_root,
            site_root=config.site_root,
        )

        # Resolve tenant
        tenant = repo.get_tenant_by_slug(config.tenant_slug)
        if tenant is None:
            print(
                f"ERROR: no tenant with slug={config.tenant_slug!r}",
                file=sys.stderr,
            )
            sys.exit(1)

        if config.slug:
            # ── Single document mode ──
            _generate_single(
                repo, seo_repo, resolver, tenant.id, config
            )
        else:
            # ── Full run: gallery + all viewer pages ──
            _generate_all(
                repo, seo_repo, resolver, tenant.id, config
            )

    finally:
        conn.close()


def _generate_single(
    repo: Repository,
    seo_repo: SeoRepository,
    resolver: PathResolver,
    tenant_id: str,
    config: GeneratorConfig,
) -> None:
    """Generate a viewer page for a single document by slug."""
    # Repository doesn't have get_document_by_slug(tenant, slug) yet,
    # so we scan once. If you add that method, swap this out.
    docs = repo.list_documents(tenant_id, limit=10000)
    docs_by_slug = {d.slug: d for d in docs}
    doc = docs_by_slug.get(config.slug)
    if doc is None:
        print(f"ERROR: no document with slug={config.slug!r}", file=sys.stderr)
        sys.exit(1)

    view = assemble_document_view(
        repo, seo_repo, doc.id, resolver, config.url_prefix
    )
    if view is None:
        print(f"ERROR: document {config.slug!r} has no SEO record", file=sys.stderr)
        sys.exit(1)

    html = render_viewer_page(view, config.site_root)
    out_dir = config.output_root / view.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"

    if config.dry_run:
        print(f"[dry-run] {out_file}  [viewer, {len(view.pages)} pages]")
    else:
        out_file.write_text(html, encoding="utf-8")
        print(f"wrote {out_file}  [viewer, {len(view.pages)} pages]")


def _generate_all(
    repo: Repository,
    seo_repo: SeoRepository,
    resolver: PathResolver,
    tenant_id: str,
    config: GeneratorConfig,
) -> None:
    """Generate gallery index + viewer pages for all qualifying documents."""
    cards = assemble_gallery(
        repo, seo_repo, tenant_id, resolver, config.url_prefix,
        status_filter=config.status_filter,
    )
    print(f"Found {len(cards)} documents with SEO records")

    # ── Gallery index ──
    gallery_html = render_gallery_page(
        cards=cards,
        title=_humanize(config.url_prefix.strip("/")),
        canonical_url=f"{config.site_root}{config.url_prefix}/",
        site_root=config.site_root,
    )
    gallery_file = config.output_root / "index.html"
    if config.dry_run:
        print(f"[dry-run] {gallery_file}  [gallery, {len(cards)} cards]")
    else:
        config.output_root.mkdir(parents=True, exist_ok=True)
        gallery_file.write_text(gallery_html, encoding="utf-8")
        print(f"wrote {gallery_file}  [gallery, {len(cards)} cards]")

    # ── Individual viewer pages ──
    all_docs = repo.list_documents(tenant_id, limit=10000)
    docs_by_slug = {d.slug: d for d in all_docs}

    for card in cards:
        slug = card.slug
        doc = docs_by_slug.get(slug)
        if doc is None:
            print(f"[skip] {slug}: not found in documents table")
            continue

        view = assemble_document_view(
            repo, seo_repo, doc.id, resolver, config.url_prefix
        )
        if view is None:
            print(f"[skip] {slug}: no SEO record")
            continue

        html = render_viewer_page(view, config.site_root)
        out_dir = config.output_root / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "index.html"

        if config.dry_run:
            print(f"[dry-run] {out_file}  [viewer, {len(view.pages)} pages]")
        else:
            out_file.write_text(html, encoding="utf-8")
            print(f"wrote {out_file}  [viewer, {len(view.pages)} pages]")


# ═══════════════════════════════════════════════════════════════
# CLI — explicit args, no environment sniffing
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate static HTML from the document registry DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dsn",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL DSN (or set DATABASE_URL env var)",
    )
    p.add_argument("--tenant-slug", required=True, dest="tenant_slug")
    p.add_argument(
        "--output-root", required=True, dest="output_root",
        help="Filesystem root where index.html files are written",
    )
    p.add_argument(
        "--media-root", required=True, dest="media_root",
        help="Filesystem root for path→URL conversion",
    )
    p.add_argument(
        "--site-root",
        default=SITE_ROOT_DEFAULT,
        dest="site_root",
        help="Public URL root (default: %(default)s)",
    )
    p.add_argument(
        "--url-prefix",
        default="/pdfs",
        dest="url_prefix",
        help="URL path prefix for documents (default: %(default)s)",
    )
    p.add_argument(
        "--slug",
        default=None,
        help="Generate only this one document (by slug)",
    )
    p.add_argument(
        "--status",
        default=None,
        choices=[s.value for s in Status],
        help="Only include documents with this status (default: all)",
    )
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    args = p.parse_args()

    if not args.dsn:
        print("ERROR: --dsn or DATABASE_URL required", file=sys.stderr)
        sys.exit(1)

    config = GeneratorConfig(
        dsn=args.dsn,
        tenant_slug=args.tenant_slug,
        output_root=Path(args.output_root).resolve(),
        media_root=Path(args.media_root).resolve(),
        site_root=args.site_root.rstrip("/"),
        url_prefix=args.url_prefix,
        slug=args.slug,
        status_filter=Status(args.status) if args.status else None,
        dry_run=args.dry_run,
    )

    run(config)


if __name__ == "__main__":
    main()
