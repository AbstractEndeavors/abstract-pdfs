from .imports import *

def build_viewer_page(
    directory: Path,
    base_url: str,
    manifest: list[dict],
    media_root: Path,
    site_root: str,
    pdf_path:str
) -> str:
    extracted_keywords = extract_keywords(manifest, 30)
    if isinstance(directory,str):
        directory = Path(directory)
    dirbase     = directory.name
    pdf_url     = manifest[0].get("schema", {}).get("url", "") or path_to_url(pdf_path)
    title       = humanize(dirbase)
    pdf_path = pdf_path or safe_join_path(directory,f"{dirbase}.pdf")

    # Document-level summary + merged keywords from the enrichment layer.
    # Falls back to the manifest-derived values if enrichment is unavailable,
    # so the viewer never ends up with the old static "Read X ..." description.
    description = extract_description(manifest)
    keywords    = ", ".join(extracted_keywords)
    try:
        doc = analyze_document(directory)
        if doc.get("description"):
            description = doc["description"]
        doc_primary = (doc.get("keywords") or {}).get("primary") or []
        if doc_primary:
            extracted_keywords = doc_primary
            keywords = (doc.get("keywords") or {}).get("meta_keywords") or ", ".join(doc_primary)
    except Exception as exc:
        import logging
        logging.getLogger("abstract_pdf").warning(
            "document-level enrichment failed for %s: %s", directory, exc
        )
    pages_js = []
    for i, entry in enumerate(manifest, 1):
        thumb = verified_url(
            entry.get("social_meta", {}).get("og:image") or entry.get("thumbnail_link", ""), media_root, site_root
        )
        pages_js.append({
            "n":     i,
            "thumb": thumb or "",
            "text":  entry.get("longdesc", "").strip(),
            "alt":   entry.get("alt", "").split(" | ")[0] or f"Page {i}",
        })

    pages_json = json.dumps(pages_js, ensure_ascii=False)
    total      = len(pages_js)

    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "description": description,
        "keywords": keywords,
        "url": pdf_url,
        "thumbnailUrl": pages_js[0]["thumb"] if pages_js else "",
        "fileFormat": "application/pdf",
        "license": manifest[0].get("license", "CC BY-SA 4.0"),
        "creditText": manifest[0].get("attribution", "Created by thedailydialectics for educational purposes"),
    }
    first_thumb = pages_js[0]["thumb"] if pages_js else ""
    tag_pills   = "".join(
        f'<span class="tag">{kw.strip()}</span>'
        for kw in (extracted_keywords or [])
    )
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  {get_meta_tags(1,pdf_path,media_root,site_root)}
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

    /* Abstract banner — shown above nav, collapsible */
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
  <a class="home" href="{SITE_ROOT}">← Home</a>
  <span style="color:#444">/</span>
  <h1>{title}</h1>
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

<!-- Abstract / description banner -->
<div class="abstract-bar" id="abstract-bar">
  <div style="flex:1">
    <p id="abstract-text">{description}</p>
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
      <a href="{pdf_url}" target="_blank" rel="noopener"
         style="margin-left:auto;font-size:.8rem;color:var(--accent);text-decoration:none">
        ⬇ Download PDF
      </a>
    </div>
    <div class="content" id="content-area">
      <iframe id="pdf-frame" src="{pdf_url}" title="{title}"></iframe>
    </div>
  </div>
</div>

<script>
const PAGES = {pages_json};
const PDF_URL = {json.dumps(pdf_url)};
const TOTAL = {total};
const KEYWORDS = {json.dumps(extract_keywords(manifest, 12))};
let cur = 1;
let fmt = 'pdf';

// ── Abstract banner ──
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

// ── Thumbnails ──
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

// ── Format buttons ──
function setFormat(f) {{
  fmt = f;
  ['pdf','images','text'].forEach(id => {{
    document.getElementById('btn-'+id).classList.toggle('active', id===f);
  }});
  renderContent();
}}

// ── Page rendering ──
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

// ── Full-text search ──
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

// ── Keyboard shortcuts ──
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

