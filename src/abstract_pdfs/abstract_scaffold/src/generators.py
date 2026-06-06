from .imports import *
from .probers import (
    keywords_from_text,
    probe_image
    )
# ─────────────────────────────────────────────────────────────────────────────
# Generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_image_info(
    img_path: Path,
    info_path:Path,
    description:str=None,
    alt:str=None,
    caption:str=None,
    longdesc:str = None,
    keywords:str = None,
    social:str = None,
    title:str = None,
    schema:str = None,
    base_url:str=None,
    media_root:str=None
) -> ImageInfoJson:
    """
    Build a fully-populated ImageInfoJson from an image file.

    media_root is the directory that maps to the URL root — e.g. /srv/media/ba
    so that /srv/media/ba/imgs/cannabis/x.webp → /imgs/cannabis/x.webp → URL.
    """
    base_url=base_url or ROOT_URL
    media_root = media_root or MEDIA_ROOT_DIR 
    w, h, size_mb = probe_image(img_path)
    stem     = get_safe_filename(img_path)
    ext      = get_safe_ext(img_path)
    media_root = makePath(media_root)
    # Compute URL path relative to media_root.
    # Walk up ancestors until we find one that is media_root, or fall back to
    # just the filename so the tool never crashes on unexpected layouts.
    try:
        rel         = safe_rel_path(img_path,media_root)
        public_path = "/" + str(rel).replace("\\", "/")
        dir_rel     = safe_rel_path(get_safe_dirname(img_path),media_root)
        dir_path    = "/" + str(dir_rel).replace("\\", "/").lstrip("/")
    except ValueError:
        # img_path is not under media_root — use the bare filename and warn
        print(
            f"  WARNING: {img_path} is not under media-root {media_root}.\n"
            f"           URL paths will only contain the filename. "
            f"Pass --media-root correctly to fix this.",
            file=sys.stderr,
        )
        public_path = "/" + img_path.name
        dir_path    = "/"

    public_url = base_url.rstrip("/") + public_path
    page_url   = base_url.rstrip("/") + dir_path
    schema = schema or ImageSchema(
        name         = stem,
        description  = description or f"Image: {stem}",
        url          = page_url,
        content_url  = public_url,
        width        = w,
        height       = h,
    )
    social = social or SocialMeta(
        og_image      = public_url,
        og_image_alt  = alt or description or caption or stem,
        twitter_image = public_url,
    )

    return ImageInfoJson(
        page_url     = page_url,
        alt          = alt or stem.replace("-", " ").replace("_", " "),
        caption      = caption or stem.replace("-", " ").replace("_", " ").title(),
        keywords_str = ",".join(w.capitalize() for w in (keywords or stem).replace("-", " ").replace("_", " ").split()[:8]),
        filename     = stem,
        ext          = ext,
        title        = title or stem.replace("-", " ").replace("_", " ").title(),
        dimensions   = {"width": w, "height": h},
        file_size    = size_mb,
        schema       = get_dict(schema),
        social_meta  = get_dict(social),
    )

def makePath(path):
    if isinstance(path,str):
        path = Path(path)
    return path
def generate_pdf_page_manifest(
    filename,
    page_i,
    text_dir,
    thumb_dir,
    pdf_dir,
    pdf_path=None,
    image=True,
    media_root=None,
    base_url=None,
    pdfs_public_url=None,
    write=True,
    overwrite=False,
    enrich=True,
    enrich_config=None,
    describe="__unset__"
    ):
        page_num = get_page_num(page_i)
        page_str = get_page_str(page_i)
        page_tag = f"{filename}_{page_str}"
        base_url=base_url or ROOT_URL
        media_root = media_root or MEDIA_ROOT_DIR 
        pdfs_public_url = pdfs_public_url  or PDFS_ROOT_DIR

        
        # Text
        longdesc = ""
        txt_file = makePath(text_dir) / f"{page_tag}.txt"
        if txt_file.exists():
            longdesc = txt_file.read_text(encoding="utf-8", errors="replace").strip()
        elif HAS_FITZ:
            if not pdf_path:
                pdf_path = os.path.join(str(pdf_dir),filename)
            doc = fitz.open(str(pdf_path))
            longdesc = doc[page_i].get_text("text").strip()

        keywords = keywords_from_text(longdesc) if longdesc else ""

        # Dimensions
        w, h = 0, 0
        if HAS_FITZ:
            if not pdf_path:
                pdf_path = os.path.join(str(pdf_dir),filename)
            doc = fitz.open(str(pdf_path))
            rect = doc[page_i].rect
            w, h = int(rect.width), int(rect.height)

        # Thumbnail
        thumb_page_path = safe_join_path(thumb_dir, page_str)
        thumb_path = safe_join_path(thumb_page_path,f"{page_tag}.png")
        dir_rel     = safe_rel_path(get_safe_dirname(thumb_path),media_root)
        dir_path    = "/" + str(dir_rel).replace("\\", "/").lstrip("/")
        info_path = safe_join_path(thumb_page_path,f"info.json")
        thumb_abs  = str(thumb_path)
        try:
            rel_thumb = safe_rel_path(thumb_path,media_root)
            thumb_url = base_url.rstrip("/") + "/" + str(rel_thumb).replace("\\", "/")
        except ValueError:
            thumb_url = base_url.rstrip("/") + f"/pdfs/{filename}/thumbnails/{page_tag}.png"

        # NLP enrichment — clean keywords + summary/description (optionally a
        # vision caption when OCR is poor).  Falls back silently to the simple
        # frequency keywords if the enrichment layer is unavailable.
        description = ""
        summary = ""
        ocr_quality = 0.0
        if enrich and longdesc:
            try:
                from abstract_pdfs.enrichment import enrich_page
                img_arg = thumb_abs if get_pathlib_path(thumb_path).exists() else None
                enriched = enrich_page(
                    longdesc,
                    image_path=img_arg,
                    scope=f"page:{int(page_num)}",
                    config=enrich_config,
                    describe=describe,
                )
                kb = enriched.get("keywords", {}) or {}
                meta_kw = kb.get("meta_keywords")
                if meta_kw:
                    keywords = meta_kw
                description = enriched.get("description") or ""
                summary = enriched.get("summary") or ""
                ocr_quality = enriched.get("ocr_quality") or 0.0
            except Exception as e:
                logger.warning(f"page enrichment failed for {page_tag}: {e}")

        social = SocialMeta(
            og_image      = thumb_url,
            og_image_alt  = thumb_url,
            twitter_image = thumb_url,
        )
        page_url   = base_url.rstrip("/") + dir_path
        alt = f"{page_tag} | page {page_num} | {pdfs_public_url}"
        caption = description or f"{filename}.pdf page {page_num}"
        title = f"{filename}.pdf_page_{page_num}"
        schema = {"name": page_tag, "url": pdfs_public_url}
        entry =PdfPageManifestEntry(
            page_url     = page_url,
            alt          = alt,
            caption      = caption,
            keywords_str = keywords,
            filename     = page_tag,
            ext          = ".png",
            title        = title,
            dimensions   = {"width": w, "height": h},
            file_size    = round(get_pathlib_path(thumb_path).stat().st_size / 1_048_576, 3) if get_pathlib_path(thumb_path).exists() else 0.0,
            longdesc     = longdesc,
            description  = description,
            summary      = summary,
            ocr_quality  = ocr_quality,
            schema       = schema,
            social_meta  = social.to_dict(),
            text_path    = str(txt_file),
            image_path   = thumb_abs,
        )
        
        if write:
            if overwrite:
                safe_dump_to_json(data=get_dict(entry),file_path=info_path)
            else:
                update_json(info_path,entry)
            
        return entry
def generate_pdf_manifest(
    pdf_path: Path,
    text_root: Path | None = None,
    thumb_root: Path | None = None,
    base_url: str | None = None,
    media_root: Path | None = None,
    pdfs_public_url: Path | None = None,
    write=True,
    overwrite=False,
    enrich=True,
    enrich_config=None,
    describe="__unset__"
) -> list[PdfPageManifestEntry]:
    """
    Build a manifest entry per PDF page.

    media_root: the volume root that maps to URL / (e.g. /srv/media/ba)
    text_root:  directory containing {base}_page_NNN.txt files
    thumb_root: directory containing {base}_page_NNN.png thumbnails

    Both default to {pdf_dir}/text/ and {pdf_dir}/thumbnails/ respectively.
    """

    base_url=base_url or ROOT_URL
    media_root = media_root or MEDIA_ROOT_DIR 
    pdfs_public_url = pdfs_public_url  or PDFS_ROOT_DIR
    if not HAS_FITZ:
        print("  ⚠  PyMuPDF (fitz) not installed — page text/dimensions will be empty.")
        print("     pip install pymupdf")
    pdf_parts = get_file_parts(pdf_path)
    pdf_path = pdf_parts.get('file_path')
    filename     = pdf_parts.get('filename')
    pdf_dir  = pdf_parts.get('dirname')
    text_dir  = text_root  or safe_join_path(pdf_dir,"text")
    thumb_dir = thumb_root or safe_join_path(pdf_dir,"thumbnails")
    
    try:
        rel = safe_rel_path(pdf_path,media_root)
        pdfs_public_url = base_url.rstrip("/") + "/" + str(rel).replace("\\", "/")
    except ValueError:
        pdfs_public_url = base_url.rstrip("/") + "/" + pdf_path.name

    entries: list[PdfPageManifestEntry] = []

    if HAS_FITZ:
        doc = fitz.open(str(pdf_path))
        page_count = doc.page_count
    else:
        page_count = _count_pdf_pages_fallback(pdf_path)
    
    for page_i in range(page_count):
        page_num = get_page_num(page_i)
        page_str = get_page_str(page_i)
        page_tag = f"{filename}_{page_str}"
        entry = generate_pdf_page_manifest(
            filename,
            page_i ,
            text_dir,
            thumb_dir,
            pdf_dir,
            pdf_path,
            media_root=media_root,
            base_url=base_url,
            pdfs_public_url=pdfs_public_url,
            write=write,
            overwrite=overwrite,
            enrich=enrich,
            enrich_config=enrich_config,
            describe=describe,
            )
        entries.append(entry)
    if HAS_FITZ:
        doc.close()

    # Document-level aggregation: one summary + merged keyword set across all
    # pages, written to {pdf_dir}/document.json so the viewer/gallery don't
    # have to re-derive a description from raw page-1 OCR.
    if enrich:
        try:
            from abstract_pdfs.enrichment import enrich_document
            page_texts = [e.longdesc for e in entries if getattr(e, "longdesc", "")]
            cover = entries[0].image_path if entries else None
            doc_result = enrich_document(
                page_texts,
                config=enrich_config,
                cover_image_path=cover,
                describe=describe,
            )
            doc_result["title"] = filename.replace("_", " ").replace("-", " ").title()
            doc_result["pdf_url"] = pdfs_public_url
            if write:
                safe_dump_to_json(
                    data=doc_result,
                    file_path=safe_join_path(pdf_dir, "document.json"),
                )
        except Exception as e:
            logger.warning(f"document-level enrichment failed for {filename}: {e}")

    return entries


def _normalize_thumbnail(value: str) -> str:
    """
    Strip leading slash and redundant 'public/' prefix.
    Canonical form is always relative to public/ root: 'imgs/section/name'.
    Storing 'public/imgs/...' causes a double-public error at build time because
    resolveThumbnailInfoJson prepends PUBLIC_ROOT (which already ends in /public).
    """
    v = value.lstrip("/")
    if v.startswith("public/"):
        v = v[len("public/"):]
    return v


def generate_page_variables(
    section:     str,
    slug:        str,
    title:       str,
    description: str,
    thumbnail:   str,
    base_url:    str,
    keywords:    str = "",
    content_file: str = "",
) -> VariablesJson:
    """Build a VariablesJson for a new page."""
    clean_base       = base_url.rstrip("/")
    href             = f"/{section}/{slug}"
    share_url        = f"{clean_base}/{section}/{slug}"
    cf               = content_file or f"contents/{section}/{slug}.md"
    thumb_normalized = _normalize_thumbnail(thumbnail)
    thumb_link       = f"{clean_base}/{thumb_normalized}/{slug}_resized.webp"

    return VariablesJson(
        BASE_URL     = clean_base,
        href         = href,
        title        = title,
        content_file = cf,
        description  = description,
        share_url    = share_url,
        keywords_str = keywords or slug.replace("-", ", "),
        thumbnail    = thumb_normalized,   # never store public/ prefix
        thumbnail_alt     = f"{title} thumbnail",
        thumbnail_caption = f"Thumbnail image for {title}",
        thumbnail_keywords_str = keywords or slug.replace("-", ", "),
        thumbnail_link    = thumb_link,
    )


def _count_pdf_pages_fallback(pdf_path: Path) -> int:
    """Count PDF pages without PyMuPDF by scanning raw bytes for /Page markers."""
    try:
        data = pdf_path.read_bytes()
        return len(re.findall(rb'/Type\s*/Page[^s]', data))
    except Exception:
        return 0



