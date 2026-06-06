from __future__ import annotations
from fix_metadata import *
import json
import os
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any


SITE_ROOT = "https://thedailydialectics.com"
MEDIA_ROOT = Path("/srv/media/thedailydialectics")
OUTPUT_ROOT = MEDIA_ROOT

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "meta",
    "pages",
    "text",
    "thumbnails",
    "preprocessed_images",
    "preprocessed_text",
}


@dataclass(slots=True)
class Card:
    title: str
    href: str
    image: str = ""
    description: str = ""
    meta: str = ""
    tags: list[str] | None = None
    kind: str = "item"  # "dir" | "item"


def safe_load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clean_text(value: Any, max_len: int = 180) -> str:
    if isinstance(value, list):
        value = " ".join(str(v) for v in value if v)
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    if len(value) <= max_len:
        return value
    return value[:max_len].rsplit(" ", 1)[0] + "…"


def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").strip().title()


def rel_url(path: Path, root: Path = OUTPUT_ROOT, site_root: str = SITE_ROOT) -> str:
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    
    return f"{site_root}/{rel}".rstrip("/")


def dir_url(directory: Path) -> str:
    return rel_url(directory)


def file_url(file_path: Path) -> str:
    return rel_url(file_path)


def child_dirs(directory: Path) -> list[Path]:
    return sorted(
        [
            d for d in directory.iterdir()
            if d.is_dir() and d.name not in SKIP_DIRS and not d.name.startswith(".")
        ],
        key=lambda p: p.name.lower(),
    )


def first_image_in_dir(directory: Path) -> Path | None:
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            return path
    return None


def load_directory_metadata(directory: Path) -> dict[str, Any]:
    candidates = [
        directory / "metadata.json",
        directory / "meta" / "metadata.json",
        directory / "info.json",
        directory / "manifest.json",
        directory / f"{directory.name}_manifest.json",
    ]
    for candidate in candidates:
        data = safe_load_json(candidate)
        if str(candidate).endswith('metadata.json') and "('thedailydialectics.com',)" in str(data):
            info_path = os.path.join(str(directory),'info.json')
            if os.path.isfile(info_path):
                analyzed_data = safe_load_from_json(info_path)
                
                nudata = get_meta_info(analyzed_data,str(directory),metadata_path=str(candidate))
                if nudata:
                    data = nudata
                    input(data)
                    safe_dump_to_json(data=data,file_path=str(candidate))
        if data:
            return data
    return {}


def metadata_image_url(metadata: dict[str, Any], directory: Path) -> str:
    candidates = [
        metadata.get("thumbnail_link"),
        metadata.get("thumbnail_url"),
        metadata.get("thumbnail_url_resized"),
        metadata.get("thumbnail_resized"),
        metadata.get("thumbnail"),
        (metadata.get("og") or {}).get("image"),
    ]

    for value in candidates:
        if not value:
            continue
        value = str(value).strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        maybe_path = Path(value)
        if maybe_path.is_absolute() and maybe_path.exists():
            return file_url(maybe_path)
        if value.startswith("/"):
            return f"{SITE_ROOT}/{value.lstrip('/')}"
        local_path = directory / value
        if local_path.exists():
            return file_url(local_path)

    fallback = first_image_in_dir(directory)
    return file_url(fallback) if fallback else ""


def metadata_keywords(metadata: dict[str, Any], limit: int = 8) -> list[str]:
    raw = metadata.get("keywords") or []
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()]
    elif not isinstance(raw, list):
        raw = []

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        value = str(item).strip()
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def metadata_title(metadata: dict[str, Any], directory: Path) -> str:
    return (
        metadata.get("title")
        or metadata.get("name")
        or humanize(directory.name)
    )


def metadata_description(metadata: dict[str, Any]) -> str:
    return clean_text(
        metadata.get("description")
        or metadata.get("description_html")
        or metadata.get("summary")
        or metadata.get("caption")
        or ""
    )


def directory_card(directory: Path) -> Card:
    metadata = load_directory_metadata(directory)
    title = metadata_title(metadata, directory)
    description = metadata_description(metadata)
    image = metadata_image_url(metadata, directory)
    tags = metadata_keywords(metadata)
    child_count = len(
        [p for p in directory.iterdir() if not p.name.startswith(".")]
    )
    meta = f"{child_count} item{'s' if child_count != 1 else ''}"

    return Card(
        title=title,
        href=f"{dir_url(directory)}/",
        image=image,
        description=description,
        meta=meta,
        tags=tags,
        kind="dir",
    )


def leaf_card(path: Path) -> Card | None:
    if path.name == "index.html":
        return None

    if path.is_dir():
        return directory_card(path)

    if path.suffix.lower() not in {".html", ".pdf"}:
        return None

    parent = path.parent
    metadata = load_directory_metadata(parent)
    title = metadata_title(metadata, parent)
    description = metadata_description(metadata)
    image = metadata_image_url(metadata, parent)
    tags = metadata_keywords(metadata)

    href = file_url(path)
    if path.name == "index.html":
        href = f"{dir_url(parent)}/"

    meta = path.suffix.lower().lstrip(".").upper()

    return Card(
        title=title,
        href=href,
        image=image,
        description=description,
        meta=meta,
        tags=tags,
        kind="item",
    )


def breadcrumbs_html(directory: Path) -> str:
    rel_parts = directory.resolve().relative_to(OUTPUT_ROOT.resolve()).parts
    crumbs = [f'<a href="{SITE_ROOT}/">Home</a>']
    acc = OUTPUT_ROOT
    for idx, part in enumerate(rel_parts):
        acc = acc / part
        is_last = idx == len(rel_parts) - 1
        label = humanize(part)
        if is_last:
            crumbs.append(f"<span>{escape(label)}</span>")
        else:
            crumbs.append(f'<a href="{dir_url(acc)}/">{escape(label)}</a>')
    return " › ".join(crumbs)


def render_card(card: Card) -> str:
    tags_html = ""
    if card.tags:
        tags_html = (
            '<div class="card-tags">'
            + "".join(f'<span class="card-tag">{escape(tag)}</span>' for tag in card.tags[:8])
            + "</div>"
        )

    image_html = (
        f'<img src="{escape(card.image)}" alt="{escape(card.title)}" loading="lazy">'
        if card.image else
        '<div class="card-image-fallback">No Preview</div>'
    )

    kind_badge = "Directory" if card.kind == "dir" else "Page"

    return f"""
    <a class="card" href="{escape(card.href)}">
      <div class="card-media">
        {image_html}
        <span class="card-kind">{kind_badge}</span>
      </div>
      <div class="card-body">
        <div class="card-title">{escape(card.title)}</div>
        <div class="card-desc">{escape(card.description)}</div>
        {tags_html}
        <div class="card-meta">{escape(card.meta)}</div>
      </div>
    </a>
    """.strip()
def fix_metadatas(page_dir):
    print(page_dir)
    image_path = os.path.join(page_dir,'image.png')
    text_path = os.path.join(page_dir,'text.txt')
    info_path = os.path.join(page_dir,'info.json')
    metadata_path = os.path.join(page_dir,'metadata.json')
    
    if os.path.isfile(info_path):
        analyzed_data = safe_load_from_json(info_path)
        if analyzed_data:
            text_content = fetch_text_content(pdf_path, i)
            analyzed_data['image_path'] = image_path
            safe_dump_to_json(file_path=info_path, data=analyzed_data)
            meta_info = get_meta_info(analyzed_data, page_dir, metadata_path)
            safe_dump_to_json(file_path=metadata_path, data=meta_info)

            return meta_info

def build_page_meta(directory: Path, cards: list[Card]) -> dict[str, str]:
    metadata = load_directory_metadata(directory)

        
    title = metadata_title(metadata, directory)
    description = metadata_description(metadata) or clean_text(
        f"Browse {title} on The Daily Dialectics. Directory contains {len(cards)} entries."
    )
    keywords = ", ".join(metadata_keywords(metadata, limit=12))
    canonical = f"{dir_url(directory)}/"
    image = metadata_image_url(metadata, directory)

    return {
        "title": title,
        "description": description,
        "keywords": keywords,
        "canonical": canonical,
        "thumbnail_link": image,
        "og": {
            "title": title,
            "description": description,
            "url": canonical,
            "image": image,
            "type": "website",
        },
        "twitter": {
            "title": title,
            "description": description,
            "image": image,
        },
    }


def render_gallery_page(directory: Path, cards: list[Card]) -> str:
    
    page_meta = build_page_meta(directory, cards)
    title = page_meta["title"]
    description = page_meta["description"]

    cards_html = "\n".join(render_card(card) for card in cards)
    
    meta_html = []
    if page_meta.get("title"):
        meta_html.append(f"<title>{escape(page_meta['title'])}</title>")
    if page_meta.get("description"):
        meta_html.append(f'<meta name="description" content="{escape(page_meta["description"])}">')
    if page_meta.get("keywords"):
        meta_html.append(f'<meta name="keywords" content="{escape(page_meta["keywords"])}">')
    if page_meta.get("canonical"):
        meta_html.append(f'<link rel="canonical" href="{escape(page_meta["canonical"])}">')
    if page_meta.get("thumbnail_link"):
        meta_html.append(f'<meta property="og:image" content="{escape(page_meta["thumbnail_link"])}">')
    meta_html.append(f'<meta property="og:title" content="{escape(title)}">')
    meta_html.append(f'<meta property="og:description" content="{escape(description)}">')
    meta_html.append(f'<meta property="og:url" content="{escape(page_meta["canonical"])}">')
    meta_html.append('<meta property="og:type" content="website">')
    meta_html.append('<meta name="twitter:card" content="summary_large_image">')
    meta_html.append(f'<meta name="twitter:title" content="{escape(title)}">')
    meta_html.append(f'<meta name="twitter:description" content="{escape(description)}">')
    if page_meta.get("thumbnail_link"):
        meta_html.append(f'<meta name="twitter:image" content="{escape(page_meta["thumbnail_link"])}">')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {' '.join(meta_html)}
  <style>
    :root {{
      --bg: #0b0f14;
      --panel: #121821;
      --panel-2: #18212c;
      --text: #ebf2f8;
      --muted: #98a6b5;
      --accent: #6ab0ff;
      --border: #273241;
      --chip: #223041;
      --shadow: 0 12px 32px rgba(0,0,0,.28);
      --radius: 16px;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }}

    a {{ color: inherit; text-decoration: none; }}

    .page {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
    }}

    .crumbs {{
      font-size: .88rem;
      color: var(--muted);
      margin-bottom: 18px;
      line-height: 1.5;
    }}

    .crumbs a {{ color: var(--accent); }}

    .hero {{
      margin-bottom: 22px;
      padding: 18px 20px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: linear-gradient(180deg, var(--panel), var(--panel-2));
      box-shadow: var(--shadow);
    }}

    .title {{
      margin: 0 0 10px;
      font-size: 1.6rem;
      line-height: 1.3;
    }}

    .description {{
      margin: 0;
      color: var(--muted);
      max-width: 900px;
      line-height: 1.55;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }}

    .card {{
      display: flex;
      flex-direction: column;
      min-width: 0;
      border: 1px solid var(--border);
      border-radius: 18px;
      overflow: hidden;
      background: var(--panel);
      box-shadow: var(--shadow);
      transition: transform .18s ease, border-color .18s ease;
    }}

    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent);
    }}

    .card-media {{
      position: relative;
      background: #0f141b;
      min-height: 180px;
    }}

    .card-media img {{
      width: 100%;
      height: 180px;
      object-fit: cover;
      display: block;
    }}

    .card-image-fallback {{
      min-height: 180px;
      display: grid;
      place-items: center;
      color: var(--muted);
      font-size: .88rem;
    }}

    .card-kind {{
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(11, 15, 20, .88);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 999px;
      padding: 4px 8px;
      font-size: .72rem;
    }}

    .card-body {{
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
    }}

    .card-title {{
      font-size: .98rem;
      font-weight: 700;
      line-height: 1.35;
    }}

    .card-desc {{
      font-size: .84rem;
      color: var(--muted);
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 5em;
    }}

    .card-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .card-tag {{
      background: var(--chip);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 4px 8px;
      font-size: .72rem;
      color: var(--text);
    }}

    .card-meta {{
      margin-top: auto;
      font-size: .74rem;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <div class="page">
    <nav class="crumbs">{breadcrumbs_html(directory)}</nav>

    <section class="hero">
      <h1 class="title">{escape(title)}</h1>
      <p class="description">{escape(description)}</p>
    </section>

    <section class="grid">
      {cards_html}
    </section>
  </div>
</body>
</html>"""


def build_cards_for_directory(directory: Path) -> list[Card]:
    cards: list[Card] = []

    for child in child_dirs(directory):
        cards.append(directory_card(child))

    for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if child.name.startswith("."):
            continue
        if child.is_dir():
            continue
        if child.name in {"index.html", "metadata.json", "info.json", "manifest.json"}:
            continue
        card = leaf_card(child)
        if card:
            cards.append(card)

    return cards


def write_directory_gallery(directory: Path) -> None:
    cards = build_cards_for_directory(directory)
    html = render_gallery_page(directory, cards)
    out_path = directory / "index.html"
    out_path.write_text(html, encoding="utf-8")


def walk_directories(root: Path) -> list[Path]:
    output: list[Path] = []
    for current, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        output.append(Path(current))
    return sorted(output, key=lambda p: len(p.parts), reverse=True)


def generate_all_directory_galleries(root: Path = OUTPUT_ROOT) -> None:
    for directory in walk_directories(root):
        if str(directory).startswith('/srv/media/thedailydialectics/pdfs') and not str(directory).endswith('page'):
            print(directory)
            write_directory_gallery(directory)


if __name__ == "__main__":
    generate_all_directory_galleries()
