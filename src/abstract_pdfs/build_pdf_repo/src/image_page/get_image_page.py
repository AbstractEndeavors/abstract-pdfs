from .imports import *



TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {{ metatags }}
  <script type="application/ld+json">{{ schema_json }}</script>

  <style>
    :root {
      --bg: #0b0f14;
      --panel: #121821;
      --panel-2: #18212c;
      --panel-3: #0f141b;
      --text: #ebf2f8;
      --muted: #98a6b5;
      --accent: #6ab0ff;
      --border: #273241;
      --chip: #223041;
      --shadow: 0 12px 32px rgba(0,0,0,.28);
      --radius: 16px;
      --side-width: 320px;
    }

    * { box-sizing: border-box; }

    html, body {
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }

    a { color: var(--accent); }

    .app {
      display: grid;
      grid-template-columns: var(--side-width) 1fr;
      min-height: 100vh;
    }

    .sidebar {
      background: var(--panel);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .sidebar-top {
      position: sticky;
      top: 0;
      z-index: 20;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
      padding: 16px;
    }

    .crumb {
      display: inline-block;
      margin-bottom: 10px;
      font-size: .92rem;
      text-decoration: none;
    }

    .title {
      margin: 0 0 10px;
      font-size: 1.15rem;
      line-height: 1.35;
    }

    .desc {
      margin: 0 0 12px;
      color: var(--muted);
      font-size: .92rem;
      line-height: 1.45;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }

    .chip {
      padding: 5px 10px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid var(--border);
      font-size: .78rem;
      color: var(--text);
    }

    .meta-box {
      display: grid;
      gap: 8px;
      padding: 12px;
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 14px;
      font-size: .84rem;
      color: var(--muted);
      line-height: 1.45;
    }

    .meta-box a {
      text-decoration: none;
    }

    .main {
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .toolbar {
      position: sticky;
      top: 0;
      z-index: 30;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      padding: 14px 18px;
      background: rgba(11,15,20,.94);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border);
    }

    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .btn, button {
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      text-decoration: none;
      font-size: .92rem;
      cursor: pointer;
    }

    .viewer-scroll {
      flex: 1;
      min-height: 0;
      overflow: auto;
      padding: 18px;
    }

    .doc-stack {
      display: grid;
      gap: 18px;
      max-width: 1100px;
      margin: 0 auto;
    }

    .page-card {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .page-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--panel-2);
    }

    .page-head-left {
      min-width: 0;
    }

    .page-number {
      font-size: .9rem;
      font-weight: 700;
    }

    .page-scope {
      color: var(--muted);
      font-size: .82rem;
      line-height: 1.3;
      margin-top: 2px;
    }

    .page-keywords {
      color: var(--muted);
      font-size: .75rem;
      text-align: right;
      max-width: 40%;
      line-height: 1.35;
    }

    .page-image-wrap {
      background: #fff;
      padding: 12px;
    }

    .page-image {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 10px;
      background: #fff;
    }

    .page-text-wrap {
      padding: 16px 18px;
      border-top: 1px solid var(--border);
    }

    .page-text-title {
      margin: 0 0 10px;
      font-size: .95rem;
      color: var(--muted);
    }

    .page-text {
      white-space: pre-wrap;
      line-height: 1.7;
      color: #dbe7f2;
      font-size: .98rem;
    }

    .caption {
      color: var(--muted);
      font-size: .88rem;
      line-height: 1.45;
      margin: 0;
    }

    @media (max-width: 980px) {
      .app {
        grid-template-columns: 1fr;
      }

      .sidebar {
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }

      .page-head {
        flex-direction: column;
        align-items: flex-start;
      }

      .page-keywords {
        max-width: none;
        text-align: left;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="sidebar-top">
        <a class="crumb" href="{{ home_url }}">← thedailydialectics</a>
        <div class="desc">{{ breadcrumbs|safe }}</div>
        <h1 class="title">{{ title }}</h1>

        {% if description %}
        <p class="desc">{{ description }}</p>
        {% endif %}

        {% if keyword_tags %}
        <div class="chips">
          {% for kw in keyword_tags %}
          <span class="chip">{{ kw }}</span>
          {% endfor %}
        </div>
        {% endif %}

        <div class="meta-box">
          {% if attribution %}<div><strong>Attribution:</strong> {{ attribution }}</div>{% endif %}
          {% if license %}<div><strong>License:</strong> {{ license }}</div>{% endif %}
          {% if parent_pdf_url %}<div><a href="{{ parent_pdf_url }}">Open parent PDF viewer</a></div>{% endif %}
          {% if img_url %}<div><a href="{{ img_url }}" target="_blank" rel="noopener">Open full image</a></div>{% endif %}
        </div>
      </div>
    </aside>

    <main class="main">
      <div class="toolbar">
        <div class="toolbar-group">
          <a class="btn" href="{{ parent_pdf_url }}">PDF viewer</a>
          {% if parent_pdf_file_url %}
          <a class="btn" href="{{ parent_pdf_file_url }}" target="_blank" rel="noopener">Download PDF</a>
          {% endif %}
          {% if img_url %}
          <a class="btn" href="{{ img_url }}" target="_blank" rel="noopener">Open image</a>
          {% endif %}
        </div>
      </div>

      <div class="viewer-scroll">
        <div class="doc-stack">
          <section class="page-card">
            <div class="page-head">
              <div class="page-head-left">
                <div class="page-number">Page {{ page_number }}</div>
                <div class="page-scope">{{ title }}</div>
              </div>
              {% if keyword_tags %}
              <div class="page-keywords">{{ keyword_tags[:8]|join(", ") }}</div>
              {% endif %}
            </div>

            {% if img_url %}
            <div class="page-image-wrap">
              <img class="page-image" src="{{ img_url }}" alt="{{ alt }}">
            </div>
            {% endif %}

            {% if alt %}
            <div class="page-text-wrap">
              <h2 class="page-text-title">Caption</h2>
              <p class="caption">{{ alt }}</p>
            </div>
            {% endif %}

            {% if page_text %}
            <div class="page-text-wrap">
              <h2 class="page-text-title">Extracted text</h2>
              <div class="page-text">{{ page_text }}</div>
            </div>
            {% endif %}
          </section>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
"""
def path_to_url(path: str, media_root: str = PDF_MEDIA_ROOT, site_root: str = SITE_ROOT) -> str:
    rel = os.path.realpath(path).replace(os.path.realpath(media_root), "").lstrip(os.sep)
    return f"{site_root}/{rel.replace(os.sep, '/')}"


def _normalize_keyword_tags(keywords) -> list[str]:
    if not keywords:
        return []
    if isinstance(keywords, str):
        return [item.strip() for item in keywords.split(",") if item.strip()]
    if isinstance(keywords, list):
        return [str(item).strip() for item in keywords if str(item).strip()]
    return []


def _clean_text(value: str, max_len: int = 220) -> str:
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    if len(value) <= max_len:
        return value
    return value[:max_len].rsplit(" ", 1)[0] + "…"


def get_image_html(
    *,
    schema_json,
    breadcrumbs,
    metatags,
    attribution,
    alt,
    keyword_tags,
    img_url,
    title,
    license,
    description,
    parent_pdf_url,
    parent_pdf_file_url,
    page_number,
    page_text,
    home_url,
):
    return Template(TEMPLATE).render(
        schema_json=schema_json,
        breadcrumbs=breadcrumbs,
        metatags=metatags,
        attribution=attribution,
        alt=alt,
        keyword_tags=keyword_tags,
        img_url=img_url,
        title=title,
        license=license,
        description=description,
        parent_pdf_url=parent_pdf_url,
        parent_pdf_file_url=parent_pdf_file_url,
        page_number=page_number,
        page_text=page_text,
        home_url=home_url,
    )


def get_image_page(image_path):
    image_file_parts = get_file_parts(image_path)
    page_dir = image_file_parts.get("dirname")
    page_num = image_file_parts.get("dirbase")
    pdf_dir = image_file_parts.get("super_dirname")
    pdf_filename = image_file_parts.get("super_dirbase")
    pdf_basename = f"{pdf_filename}.pdf"
    pdf_path = os.path.join(pdf_dir, pdf_basename)

    metadata_path = os.path.join(page_dir, "metadata.json")
    metadata = safe_load_from_json(metadata_path) if os.path.isfile(metadata_path) else {}

    info_path = os.path.join(page_dir, "info.json")
    info = safe_load_from_json(info_path) if os.path.isfile(info_path) else {}

    image_path = os.path.join(page_dir, "image.png")
    if not os.path.isfile(image_path):
        for candidate in ("image.webp", "image.jpg", "image.jpeg"):
            candidate_path = os.path.join(page_dir, candidate)
            if os.path.isfile(candidate_path):
                image_path = candidate_path
                break

    image_url = path_to_url(image_path, media_root=MEDIA_ROOT, site_root=ROOT_URL)

    text_path = os.path.join(page_dir, "text.txt")
    text = read_from_file(text_path) if os.path.isfile(text_path) else ""
    html_path = os.path.join(page_dir, "index.html")

    schema = metadata.get("schema") or {}
    title = metadata.get("title") or info.get("scope") or humanize(page_num)
    alt = metadata.get("alt") or f"{pdf_filename} page {page_num}"
    description = metadata.get("description") or _clean_text(text or alt)
    keyword_tags = _normalize_keyword_tags(metadata.get("keywords") or ((info.get("keywords") or {}).get("primary") or []))

    parent_pdf_url = path_to_url(pdf_dir, media_root=MEDIA_ROOT, site_root=ROOT_URL)

    parent_pdf_file_url = path_to_url(pdf_path) if os.path.isfile(pdf_path) else ""
    metatags = generate_meta_tags(metadata, "https://thedailydialectics.com")
    bread_crumbs = breadcrumbs(image_url)
    license_text = "CC BY-SA 4.0 · Created by The Daily Dialectics for educational purposes"
    attribution = "@thedailydialectics"

    html = get_image_html(
        metatags=metatags,
        schema_json=json.dumps(schema, ensure_ascii=False),
        breadcrumbs=bread_crumbs,
        title=title,
        img_url=image_url,
        alt=alt,
        keyword_tags=keyword_tags,
        description=description,
        license=license_text,
        attribution=attribution,
        parent_pdf_url=parent_pdf_url,
        parent_pdf_file_url=parent_pdf_file_url,
        page_number=page_num,
        page_text=text,
        home_url="https://thedailydialectics.com",
    )

    write_to_file(file_path=html_path, contents=html)
    return html
