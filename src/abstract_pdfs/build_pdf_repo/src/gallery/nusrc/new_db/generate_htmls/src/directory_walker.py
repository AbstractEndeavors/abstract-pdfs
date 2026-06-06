from .imports import *
from .template_registry import *
from .assembly import *
from .helpers import *
from .rendering import *
# ═══════════════════════════════════════════════════════════════
# Directory walker — the recursive orchestrator
# ═══════════════════════════════════════════════════════════════


@dataclass
class WalkConfig:
    """All the explicit wiring a walk needs."""
    site_root: str
    dry_run: bool
    templates: TemplateRegistry
    resolver: PathResolver
    doc_index: DocumentIndex


def _write_html(path: Path, html: str, label: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] {path}  [{label}]")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        print(f"wrote {path}  [{label}]")


def _load_page_metadata(page_dir: Path) -> dict:
    """
    Load metadata from a page directory.
    Merges info.json and metadata.json into a single dict.
    """
    metadata = {}
    
    # info.json has basic image/caption info
    info_path = page_dir / "info.json"
    if info_path.exists():
        try:
            metadata.update(json.loads(info_path.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Bad info.json in %s: %s", page_dir, e)
    
    # metadata.json has SEO-specific fields (title, description, keywords, etc.)
    meta_path = page_dir / "metadata.json"
    if meta_path.exists():
        try:
            metadata.update(json.loads(meta_path.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Bad metadata.json in %s: %s", page_dir, e)
    
    return metadata


def _generate_page_seo_page(
    page_dir: Path,
    page_num: int,
    document: Any,
    view: DocumentView,
    config: WalkConfig,
    base_url: str,
) -> None:
    """
    Generate individual SEO page for a page directory.
    
    Each page gets a dedicated HTML with:
    - Page image from image.png
    - OCR text from text.txt
    - SEO metadata from metadata.json + info.json
    - Structured schema for the page
    """
    out_file = page_dir / "index.html"
    
    # Load metadata
    metadata = _load_page_metadata(page_dir)
    
    # Resolve paths
    image_path = page_dir / "image.png"
    text_path = page_dir / "text.txt"
    
    image_url = config.resolver.to_url_if_exists(str(image_path)) if image_path.exists() else None
    ocr_text = read_text_file(str(text_path)) if text_path.exists() else ""
    
    # Extract SEO fields with sensible fallbacks
    page_title = metadata.get("title") or f"{view.title} — Page {page_num}"
    description = metadata.get("description") or clean_text(ocr_text or view.description, 300)
    keywords = metadata.get("keywords") or view.keywords
    alt_text = metadata.get("alt") or f"Page {page_num} of {view.title}"
    
    # Social metadata from info.json
    social_meta = metadata.get("social_meta", {})
    og_image = social_meta.get("og:image") or image_url
    
    # Build canonical URL for this page
    # Assuming base_url is the document dir, pages are at base_url/pages/XXXX/
    page_canonical = f"{base_url.rstrip('/')}/pages/{page_dir.name}/"
    index_url = base_url.rstrip("/") + "/"
    
    # Render the page
    html = render_page_seo(
        config.templates,
        page_title=page_title,
        description=description,
        keywords=keywords,
        alt_text=alt_text,
        image_url=image_url,
        ocr_text=ocr_text,
        page_num=page_num,
        document_title=view.title,
        document_keywords=view.keywords,
        canonical_url=page_canonical,
        og_image=og_image,
        page_url=page_canonical,
        document_url=index_url,
        site_root=config.site_root,
        schema_data=metadata.get("schema", {}),
    )
    
    _write_html(out_file, html, f"page SEO, page {page_num}", config.dry_run)


def _generate_pages_for_document(
    document_dir: Path,
    base_url: str,
    document: Any,
    view: DocumentView,
    config: WalkConfig,
) -> None:
    """
    Generate SEO pages for all pages under pages/ subdirectory.
    
    Looks for document_dir/pages/XXXX/ directories and renders each one.
    """
    pages_dir = document_dir / "pages"
    if not pages_dir.exists():
        return
    
    # Find all page directories (0001, 0002, etc.)
    page_dirs = sorted(
        d for d in pages_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    
    for i, page_dir in enumerate(page_dirs, 1):
        _generate_page_seo_page(
            page_dir=page_dir,
            page_num=i,
            document=document,
            view=view,
            config=config,
            base_url=base_url,
        )


def generate_for_directory(
    directory: Path,
    base_url: str,
    config: WalkConfig,
    recurse: bool = True,
) -> bool:
    """
    Generate index.html for this directory. Returns True if something was written.

    Decision order:
      1. Does this dir match a DB document with SEO? → viewer page + page SEO pages
      2. Does this dir have a filesystem manifest?   → viewer page (filesystem fallback)
      3. Does this dir have info.json?               → image page
      4. Does this dir have children?                → gallery page
      5. Otherwise                                   → skip
    """
    out_file = directory / "index.html"

    # ── 1. DB document match → viewer page ──
    doc = config.doc_index.find_by_dir(directory)
    if doc:
        view = config.doc_index.assemble_view(
            doc.id, config.resolver, base_url
        )
        if view and view.pages:
            html = render_viewer(config.templates, view, config.site_root,directory)
            _write_html(out_file, html, f"viewer, {len(view.pages)} pages", config.dry_run)
            
            # Generate individual page SEO pages (pages/XXXX/index.html)
            _generate_pages_for_document(
                document_dir=directory,
                base_url=base_url,
                document=doc,
                view=view,
                config=config,
            )
            
            # Viewer pages are leaves — don't recurse into their subdirs
            return True

    # ── 2. Filesystem manifest (not yet in DB) → viewer page ──
    # Preserves v5 behavior for dirs that haven't been ingested yet
    manifest = load_manifest(directory)
    if manifest:
        html = _render_manifest_viewer(
            directory, base_url, manifest, config
        )
        _write_html(out_file, html, f"viewer/manifest, {len(manifest)} pages", config.dry_run)
        return True

    # ── 3. info.json → image page ──
    info_path = directory / "info.json"
    if info_path.exists():
        try:
            meta = json.loads(info_path.read_text())
            html = render_image_page(
                config.templates, meta, base_url,
                config.site_root, directory, config.resolver,
            )
            _write_html(out_file, html, "image page", config.dry_run)
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Bad info.json %s: %s", info_path, e)

    # ── 4. Branch dir with children → gallery ──
    children = child_dirs(directory)
    if not children:
        return False

    # Recurse first so child pages exist before we build the gallery
    if recurse:
        for child in children:
            child_url = f"{base_url.rstrip('/')}/{child.name}"
            generate_for_directory(child, child_url, config, recurse=True)

    # Build gallery cards for immediate children
    cards = [
        config.doc_index.make_card_for_dir(
            child,
            href=f"{base_url.rstrip('/')}/{child.name}/",
            resolver=config.resolver,
        )
        for child in children
    ]

    html = render_gallery(
        config.templates, cards, humanize(directory.name),
        base_url, config.site_root,
    )
    _write_html(out_file, html, f"gallery, {len(cards)} cards", config.dry_run)
    return True


def _render_manifest_viewer(
    directory: Path,
    base_url: str,
    manifest: list[dict],
    config: WalkConfig,
) -> str:
    """
    Render a viewer page from a filesystem manifest (not yet in DB).
    This is the backward-compat path for dirs that haven't been ingested.
    Uses the same viewer template, just assembles context differently.
    """
    title = humanize(directory.name)
    first = manifest[0]
    description = clean_text(
        first.get("longdesc") or first.get("caption") or "", 300
    )
    keywords_raw = set()
    for entry in manifest:
        for kw in entry.get("keywords_str", "").split(","):
            kw = kw.strip()
            if kw and len(kw) > 2:
                keywords_raw.add(kw)
    keywords = ", ".join(sorted(keywords_raw)[:30])
    keywords_list = sorted(keywords_raw)[:12]

    pages_js = []
    for i, entry in enumerate(manifest, 1):
        thumb = entry.get("social_meta", {}).get("og:image")
        pages_js.append({
            "n": i,
            "thumb": thumb or "",
            "text": entry.get("longdesc", "").strip(),
            "alt": entry.get("alt", "").split(" | ")[0] or f"Page {i}",
        })

    pdf_url = first.get("schema", {}).get("url", "")
    first_thumb = pages_js[0]["thumb"] if pages_js else ""

    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "description": description,
        "keywords": keywords,
        "url": pdf_url,
        "thumbnailUrl": first_thumb,
        "fileFormat": "application/pdf",
    }

    return config.templates.render(
        "viewer",
        title=title,
        description=description,
        keywords=keywords,
        canonical_url=base_url.rstrip("/") + "/",
        first_thumb=first_thumb,
        schema_json=json.dumps(schema, indent=2),
        site_root=config.site_root,
        total=len(pages_js),
        pdf_url=pdf_url,
        pages_json=json.dumps(pages_js, ensure_ascii=False),
        pdf_url_json=json.dumps(pdf_url),
        keywords_json=json.dumps(keywords_list),
    )
