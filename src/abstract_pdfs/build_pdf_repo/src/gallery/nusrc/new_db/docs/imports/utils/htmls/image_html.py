from .imports import URL_ROOT,generate_meta_tags
from .utils import create_bread_crumbs
import json
def build_image_html(meta: dict, href: str,thumbnail_url=None,text=None,  path=None) -> str:
    
    meta['variants'] = ['https://thedailydialectics.com']
    og    = meta.get("og", {}) or {}
    tw    = meta.get("twitter", {}) or {}
    other = meta.get("other", {}) or {}
    art   = og.get("article", {}) or {}
    description   = meta.get("description", {}) or {}
    domain = tw.get("domain", "")

    domain = tw.get("domain", "")
    if isinstance(domain, list):
        domain = domain[0] if domain else ""

    tag_metas = "".join(
        f'  <meta property="article:tag" content="{t}">\n'
        for t in (art.get("tag") or [])
    )
    article_metas = "".join(
        f'  <meta property="article:{k}" content="{v}">\n'
        for k, v in art.items()
        if k != "tag" and v
    )
    other_metas = "".join(
        f'  <meta name="{k}" content="{v}">\n'
        for k, v in other.items()
        if v and k not in ("alternate", "geo", "hreflang") and not isinstance(v, dict)
    )
    title = meta.get("title", "")
    breadcrumbs = create_bread_crumbs(path) if path else ""
    description = meta.get("description", "")
    keywords    = meta.get("keywords", "")
    canonical   = meta.get("canonical", href)
    schema = {
        "@context":    "https://schema.org",
        "@type":       "CreativeWork",
        "name":        title,
        "description": description,
        "keywords":    keywords,
        "url":         href,
        "thumbnailUrl": thumbnail_url,
        "fileFormat":  "application/pdf",
        "license":     "CC BY-SA 4.0",
        "creditText":  "Created by thedailydialectics for educational purposes",
    }
    first_thumb = thumbnail_url

 
    tags_html   = "".join(
        f'<span class="tag">{kw.strip()}</span>'
        for kw in (meta.get("keywords") or [])
    )
    meta_tags = generate_meta_tags(meta, base_url='https://thedailydialectics.com', json_path=None)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="{other.get('charset', 'UTF-8')}">
  <meta name="viewport" content="{other.get('viewport', 'width=device-width,initial-scale=1')}">
  <meta name="theme-color" content="{other.get('theme_color', '#FFFFFF')}">
  <meta name="color-scheme" content="{other.get('color_scheme', 'light')}">
  {meta_tags}
  <script type="application/ld+json">{json.dumps(schema, indent=2)}</script>

  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0d0d0d; --surface: #1a1a1a; --surface2: #222;
      --text: #e0e0e0; --muted: #888; --accent: #7aaeff;
    }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
            display: flex; flex-direction: column; min-height: 100vh; }}

    .topbar {{ display: flex; align-items: center; gap: .6rem; padding: .5rem .8rem;
               background: var(--surface); border-bottom: 1px solid #333; flex-wrap: wrap; }}
    .topbar a.home {{ color: var(--muted); font-size: .8rem; text-decoration: none; }}
    .topbar a.home:hover {{ color: var(--text); }}
    .topbar h1 {{ font-size: .95rem; font-weight: 600; flex: 1;
                  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

    .abstract-bar {{ background: #111; border-bottom: 1px solid #2a2a2a;
                     padding: .5rem 1rem; font-size: .8rem; color: #999;
                     display: flex; align-items: flex-start; gap: .6rem; }}
    .abstract-bar p {{ flex: 1; line-height: 1.5; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: .25rem; margin-top: .3rem; }}
    .card-tag {{ background: #1e1e1e; border: 1px solid #2e2e2e; border-radius: 3px;
                  padding: .1rem .4rem; font-size: .68rem; color: #666; }}
    .abstract-toggle {{ cursor: pointer; color: var(--muted); font-size: .75rem;
                         white-space: nowrap; user-select: none; }}
    .abstract-toggle:hover {{ color: var(--text); }}

    nav.breadcrumb {{ font-size: .8rem; color: #888; padding: .5rem 1rem;
                      background: var(--surface2); border-bottom: 1px solid #2a2a2a; }}
    nav.breadcrumb a {{ color: #aaa; text-decoration: none; }}
    nav.breadcrumb a:hover {{ color: #fff; }}

    .content {{ flex: 1; display: flex; justify-content: center;
                align-items: flex-start; padding: 1.5rem 1rem; }}
    .image-wrap {{ max-width: 860px; width: 100%; }}
    .image-wrap img {{ width: 100%; height: auto; display: block;
                       border-radius: 4px; border: 1px solid #2a2a2a; }}
    .image-wrap .caption {{ font-size: .8rem; color: var(--muted);
                             margin-top: .5rem; line-height: 1.5; }}

    .page-text {{ max-width: 860px; width: 100%; margin: 1.5rem auto;
                  padding: 0 1rem; }}
    .page-text pre {{ white-space: pre-wrap; font-size: .85rem; line-height: 1.6;
                      color: #ccc; font-family: 'Courier New', monospace;
                      background: var(--surface); padding: 1rem;
                      border-radius: 4px; border: 1px solid #2a2a2a; }}
  </style>
</head>
<body>

<div class="topbar">
  <a class="home" href="https://thedailydialectics.com">← Home</a>
  <span style="color:#444">/</span>
  <h1>{title}</h1>
</div>

<div class="abstract-bar" id="abstract-bar">
  <div style="flex:1">
    <p>{description[:300]}</p>
    <div class="tags">{tags_html}</div>
  </div>
  <span class="abstract-toggle" onclick="
    const c=this.previousElementSibling;
    const hidden=c.style.display==='none';
    c.style.display=hidden?'':'none';
    this.textContent=hidden?'▲ hide':'▼ show info';
  ">▲ hide</span>
</div>

{breadcrumbs}

<div class="content">
  <div class="image-wrap">
    <a href="{href}">
      <img src="{thumbnail_url}"
           alt="{og.get('image_alt', title)}"
           loading="lazy">
    </a>
    <p class="caption">{description[:200]}</p>
  </div>
</div>

{'<div class="page-text"><pre>' + text + '</pre></div>' if text else ''}

</body>
</html>"""

