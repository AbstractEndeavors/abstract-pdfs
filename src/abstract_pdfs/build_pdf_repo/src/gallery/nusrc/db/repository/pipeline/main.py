import logging

logging.getLogger("pydot").setLevel(logging.WARNING)
logging.getLogger("pypdf").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.WARNING)
from .imports import *
from .constants import *
from .meta_info import get_meta_info
from abstract_utilities import safe_load_from_json,read_from_file,get_file_parts,safe_join
from abstract_apis import postRequest
from abstract_pdfs import extract_single_pdf_page_text
import shutil
# At the very top of run_pipeline.py, before any imports

# ── Pipeline ─────────────────────────────────────────────────
def is_read_error(value):
    if not value or value =="No Content":
        return True
    if isinstance(value,dict):
        if value.get("error") == "Input has 2 word(s); need at least 10 for a meaningful summary.":
            return True
    
def _load_json(path: Path) -> dict | None:
    if not os.path.exists(str(path)):
        return None
    with open(path) as f:
        return json.load(f)
    
def should_analyze(path,force=False):
    logger.info(f"starting should analyze")
    path_str = str(path)
    if force or not os.path.exists(path_str) or path.stat().st_size == 0:
        logger.info(f"should analyze")
        return True
    if path_str.endswith('.json'):
        try:
            logger.info(f"loading_json")
            value =safe_load_from_json(path_str)
            logger.info(f"json loaded")
        except:
            return True
    else:
        logger.info(f"reading file")
        value = read_from_file(path_str)
        logger.info(f"file read")
    if is_read_error(value):
        logger.info(f"no value for value == {value}")
        return True
    return value                    
def remove_directory(directory):
    delete_dirs = "/var/www/ABSTRACT_ENDEAVORS/media/TDD/delete_dirs"
    shutil.rmtree(directory)
    if os.path.isdir(directory):
        shutil.move(directory,delete_dirs)
def delete_id_three(page_dir):
    dir_page_no = os.path.basename(str(page_dir))
    if len(str(dir_page_no)) == 3:
        remove_directory(page_dir)
        logger.info(f"removed {page_dir}")
        return True
# ── Pipeline ─────────────────────────────────────────────────
def is_pdf_valid(pdf_path: Path) -> bool:
    """Check if PDF is readable and has pages."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return False
        return True
    except Exception as e:
        logger.warning(f"PDF validation failed for {pdf_path}: {e}")
        return False

def run_pipeline() -> None:
    conn = psycopg.connect(conninfo=DATABASE_URL, autocommit=True)
    try:
        repo = Repository(conn)
        seo = SeoRepository(conn)

        # ensure tenant exists
        tenant = repo.get_tenant_by_slug(TENANT_SLUG)
        if tenant is None:
            tenant = repo.insert_tenant(name=TENANT_NAME, slug=TENANT_SLUG)
            logger.info("Created tenant: %s (%s)", tenant.slug, tenant.id)

        # discover PDFs
        _dirs, all_pdfs = get_files_and_dirs(PDFS_ROOT, allowed_exts=".pdf")
        logger.info("Found %d PDFs in %s", len(all_pdfs), PDFS_ROOT)
        
        for pdf_path in all_pdfs:
            print(pdf_path)
            pdf_file_parts = get_file_parts(pdf_path)
            try:
                base_dir = pdf_file_parts.get('dirname')
                slug = pdf_file_parts.get('dirbase')
                
                # Check if already ingested (unless force=True)
                doc_hash = identity_hash(slug)
                existing_doc = repo.get_document_by_hash(tenant.id, doc_hash)
                
                if existing_doc and existing_doc.status == Status.COMPLETE and not FORCE:
                    logger.info("Skipping already-complete document: %s", slug)
                    continue
                
                ingest_document(
                    repo=repo,
                    seo=seo,
                    tenant_id=tenant.id,
                    pdf_path=pdf_path,
                    dpi=DPI,
                    force=FORCE,
                )
            except Exception:
                logger.exception("Failed to ingest %s", pdf_path)
                continue

    finally:
        conn.close()


def ingest_document(
    repo: Repository,
    seo: SeoRepository,
    tenant_id: str,
    pdf_path: Path,
    dpi: int,
    force: bool = False,
) -> None:
    pdf_file_parts = get_file_parts(pdf_path)
    
    base_dir = pdf_file_parts.get('dirname')
    slug = pdf_file_parts.get('dirbase')
    pages_dir = safe_join(base_dir,"pages")

    logger.info("Ingesting: %s", pdf_path)

    # ── register document ──
    doc = repo.upsert_document(
        tenant_id=tenant_id,
        slug=slug,
        base_path=str(base_dir),
        pdf_path=str(pdf_path),
    )
    repo.update_document_status(doc.id, Status.INGESTING)
    run = repo.start_pipeline_run(doc.id, stage="ingest")

    try:
        # ── render PDF to page images ──
        result = render_pdf_pages(
            pdf_path=pdf_path,
            output_dir=base_dir,
            dpi=dpi,
            fmt="png",
        )
        repo.update_page_count(doc.id, result.total_pages)

        # ── process each page ──
        page_dirs = sorted(Path(pages_dir).iterdir()) if os.path.exists(str(pages_dir)) else []
        page_metas: list[dict] = []

        for page_dir in page_dirs:
            if not page_dir.is_dir() or delete_id_three(page_dir) == True:
                continue
                    
               
            page_number = int(page_dir.name)

            meta = process_page(
                repo=repo,
                seo_repo=seo,
                document_id=doc.id,
                page_number=page_number,
                page_dir=page_dir,
                force=force,
                pdf_path=pdf_path
            )
            page_metas.append(meta)

        # ── document-level SEO (derived from first page's meta) ──
        if page_metas:
            seo.upsert_seo_from_dict(doc.id, page_metas[0])
            logger.info("  SEO metadata stored for document %d", doc.id)

        # ── done ──
        repo.update_document_status(doc.id, Status.COMPLETE)
        repo.complete_pipeline_run(run.id)
        logger.info("  Complete: document %d (%d pages)", doc.id, result.total_pages)

    except Exception as exc:
        repo.update_document_status(doc.id, Status.FAILED)
        repo.fail_pipeline_run(run.id, str(exc))
        raise


def process_page(
    repo: Repository,
    seo_repo: SeoRepository,
    document_id: int,
    page_number: int,
    page_dir: Path,
    force: bool = False,
    pdf_path=None
) -> dict:
    """
    Process a single page: OCR, analysis, meta info, DB registration.
    """
    image_path = page_dir / "image.png"
    text_path = page_dir / "text.txt"
    info_path = page_dir / "info.json"
    metadata_path = page_dir / "metadata.json"
    
    # ── register page in DB first ──
    page = repo.upsert_page(
        document_id=document_id,
        page_number=page_number,
        image_path=str(image_path),
        text_path=str(text_path),
        info_path=str(info_path),
        metadata_path=str(metadata_path),
    )
    
    # ── OCR (skip if text.txt exists and has content) ──
    page_text = should_analyze(text_path, force=force)
    
    
    if page_text == True:
        
        try:
            page_text = extract_single_pdf_page_text(str(pdf_path), page_number)
            write_to_file(file_path=str(text_path), contents=page_text)
            repo.update_page_ocr_status(page.id, True)
            logger.info(f"OCR completed for page {page_number}")
        except Exception as e:
            print(f"{e}")
    else:
        # Text already exists, mark as processed
        repo.update_page_ocr_status(page.id, True)
        logger.info(f"OCR skipped for page {page_number} (text.txt exists)")
    
    # ── analysis (skip if info.json exists) ──
    analyzed_data = should_analyze(info_path, force=force)
    if analyzed_data == True:
        data = {
            "text": page_text,
            "scope": f"page:{page_number}",
            "summary_preset": "brief",
            "keyword_preset": "seo",
            "input_policy": "allow"
        }
        analyzed_data = postRequest('https://clownworld.biz/hugpy/analyze/text', data=data)
        analyzed_data["image_path"] = str(image_path)
        safe_dump_to_json(file_path=str(info_path), data=analyzed_data)
        logger.info("  Page %d: analysis completed", page_number)
    else:
        logger.info("  Page %d: analysis skipped (info.json exists)", page_number)

    # ── meta info (skip if metadata.json exists) ──
    meta_info = should_analyze(metadata_path, force=force)
    if meta_info == True:
        meta_info = get_meta_info(analyzed_data, page_dir, metadata_path)
        logger.info("  Page %d: meta info completed", page_number)
    else:
        meta_info = _load_json(metadata_path) or {}
        logger.info("  Page %d: meta info skipped (metadata.json exists)", page_number)

    # ── store analysis in DB ──
    summary = analyzed_data.get("summary", "")
    keywords = analyzed_data.get("keywords", {})

    if keywords:
        seo_repo.ingest_page_analysis(
            page_id=page.id,
            summary=summary,
            keywords=keywords,
            model_version=analyzed_data.get("model_version"),
        )

    # ── store meta info in DB ──
    seo_repo.upsert_page_meta(page_id=page.id, meta=meta_info)

    return meta_info

