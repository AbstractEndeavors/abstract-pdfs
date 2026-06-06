from .imports import *
from .template_registry import *
from .helpers import *
# ═══════════════════════════════════════════════════════════════
# Rendering — templates + context
# ═══════════════════════════════════════════════════════════════
def get_keyword_list(kw):
    if kw and isinstance(kw,list):
        return kw
    if kw and isinstance(kw,str):
        return [eatAll(key,' ') for key in kw.split(',')]
    if kw:
        return list(kw)
    return []

def _find_pdf_in_directory(directory: Path) -> str | None:
    """
    Find the only .pdf file in a directory.
    Returns the relative path from directory root or None if not found.
    """
    pdfs = list(directory.glob("*.pdf"))
    if pdfs:
        return pdfs[0].name  # Just the filename, not full path
    return None


def render_viewer(
    templates: TemplateRegistry,
    view: DocumentView,
    site_root: str,
    document_dir: Path,
) -> str:
    """
    Render the PDF document viewer (index.html for the document).
    
    This is a single-page viewer that displays all pages.
    Automatically finds the PDF in the document directory.
    """
    # Find PDF in the document directory
    pdf_filename = _find_pdf_in_directory(document_dir)
    if not pdf_filename:
        # If no PDF found, this is a problem—but continue with empty
        pdf_filename = ""
    
    pages_js = [
        {
            "n": pv.page_number,
            "thumb": pv.image_url or "",
            "text": pv.text,
            "alt": pv.alt.split(" | ")[0] if pv.alt else f"Page {pv.page_number}",
        }
        for pv in view.pages
    ]
    keywords_list = [
        kw.strip()
        for kw in get_keyword_list(view.keywords)
        if kw.strip() and len(kw.strip()) > 2
    ][:12]
    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": view.title,
        "description": clean_text(view.description, 300),
        "keywords": view.keywords,
        "url": "",  # Will be relative/internal
        "thumbnailUrl": view.thumbnail_url or "",
        "fileFormat": "application/pdf",
    }

    return templates.render(
        "viewer",
        title=view.title,
        description=clean_text(view.description, 300),
        keywords=view.keywords,
        canonical_url=view.canonical_url,
        first_thumb=pages_js[0]["thumb"] if pages_js else "",
        schema_json=json.dumps(schema, indent=2),
        site_root=site_root,
        total=len(view.pages),
        pages_json=json.dumps(pages_js, ensure_ascii=False),
        pdf_filename_json=json.dumps(pdf_filename),
        keywords_json=json.dumps(keywords_list),
    )


def render_page_seo(
    templates: TemplateRegistry,
    page_title: str,
    description: str,
    keywords: str,
    alt_text: str,
    image_url: str | None,
    ocr_text: str,
    page_num: int,
    document_title: str,
    document_keywords: str,
    canonical_url: str,
    og_image: str | None,
    page_url: str,
    document_url: str,
    site_root: str,
    schema_data: dict | None = None,
) -> str:
    """
    Render an individual page SEO page.
    
    This page:
    - Has full SEO metadata for this specific page
    - Displays the page image and OCR text
    - Links back to the document viewer
    - Can be indexed and linked directly
    """
    
    # Build schema for this page
    schema = {
        "@context": "https://schema.org",
        "@type": "ImageObject",
        "name": page_title,
        "description": clean_text(description, 300),
        "url": page_url,
        "image": image_url or "",
        "isPartOf": {
            "@type": "CreativeWork",
            "name": document_title,
            "url": document_url,
        },
    }
    
    # Merge with any provided schema data
    if schema_data:
        schema.update(schema_data)
    
    # Extract keywords for JSON
    keywords_list = [
        kw.strip()
        for kw in get_keyword_list(keywords)
        if kw.strip() and len(kw.strip()) > 2
    ][:12]
    
    return templates.render(
        "page_seo",
        title=page_title,
        description=clean_text(description, 300),
        keywords=keywords,
        keywords_list=keywords_list,
        alt_text=alt_text,
        image_url=image_url or "",
        og_image=og_image or image_url or "",
        ocr_text=ocr_text,
        page_num=page_num,
        document_title=document_title,
        document_keywords=document_keywords,
        canonical_url=canonical_url,
        document_url=document_url,
        site_root=site_root,
        schema_json=json.dumps(schema, indent=2),
    )


def render_gallery(
    templates: TemplateRegistry,
    cards: list[GalleryCard],
    title: str,
    base_url: str,
    site_root: str,
) -> str:
    canonical = base_url.rstrip("/") + "/"
    card_dicts = [
        {
            "title": c.title,
            "description": c.description,
            "image_url": c.image_url,
            "href": c.href,
            "tags": c.tags,
            "page_count": c.page_count,
        }
        for c in cards
    ]
    return templates.render(
        "gallery",
        page_title=title,
        canonical_url=canonical,
        breadcrumbs=breadcrumbs_html(base_url, site_root),
        heading=title,
        card_count=len(cards),
        cards=card_dicts,
    )


def render_image_page(
    templates: TemplateRegistry,
    meta: dict[str, Any],
    base_url: str,
    site_root: str,
    directory: Path,
    resolver: PathResolver,
) -> str:
    title = meta.get("title") or humanize(directory.name)
    alt = meta.get("alt") or title
    description = clean_text(
        meta.get("longdesc") or meta.get("caption") or "", 300
    )
    keywords = meta.get("keywords_str", "")
    img_url = (
        meta.get("schema", {}).get("url")
        or meta.get("social_meta", {}).get("og:image")
    )
    # Filesystem fallback for image
    if not img_url:
        img_url = first_image_url(directory, resolver)

    keyword_tags = [kw.strip() for kw in get_keyword_list(keywords) if kw.strip()]

    return templates.render(
        "image_page",
        title=title,
        alt=alt,
        description=description,
        keywords=keywords,
        keyword_tags=keyword_tags,
        img_url=img_url,
        og_image=img_url or "",
        schema_json=json.dumps(meta.get("schema", {}), indent=2),
        license=meta.get("license", ""),
        attribution=meta.get("attribution", ""),
        canonical_url=base_url.rstrip("/") + "/",
        breadcrumbs=breadcrumbs_html(base_url, site_root),
    )
