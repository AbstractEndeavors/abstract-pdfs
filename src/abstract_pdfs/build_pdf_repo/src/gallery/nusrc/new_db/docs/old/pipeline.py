"""
pipeline.py — Document ingestion pipeline.

Walks a PDF directory, renders pages, runs OCR + analysis,
and registers everything in the database.

Dependencies:
    pip install PyMuPDF psycopg2-binary

Expects these to exist in your codebase:
    - abstract_utilities (your existing library)
    - pdf_renderer.render_pdf_pages
    - repository.Repository
    - repository_seo.SeoRepository
"""

from __future__ import annotations
from abstract_database import get_db_connection,get_cur_conn
import json
import logging
import os
from pathlib import Path


from abstract_utilities import (write_to_file,safe_dump_to_json,get_files_and_dirs)
from imports import (
    get_meta_info
)
from processing import (
    
    image_to_text,
    analyze_page
)
from pdf_renderer import render_pdf_pages
from repository import Repository, Status, identity_hash
from repository_seo import SeoRepository

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ── Config ───────────────────────────────────────────────────

PDFS_ROOT = os.environ.get("PDFS_ROOT", "/var/www/ABSTRACT_ENDEAVORS/media/TDD/pdfs")

TENANT_SLUG = os.environ.get("TENANT_SLUG", "default")
TENANT_NAME = os.environ.get("TENANT_NAME", "Default Tenant")
DPI = int(os.environ.get("RENDER_DPI", "200"))


# ── Pipeline ─────────────────────────────────────────────────


def run_pipeline() -> None:
    get_db_connection(
        name="tdd_docs",
        user="putkoff",
        env_path='/home/solcatcher/.env.d/database.env'
    )
    _,conn = get_cur_conn()
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
            try:
                ingest_document(
                    repo=repo,
                    seo=seo,
                    tenant_id=tenant.id,
                    pdf_path=Path(pdf_path),
                    dpi=DPI,
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
) -> None:
    base_dir = pdf_path.parent
    slug = base_dir.name
    pages_dir = base_dir / "pages"

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
        page_dirs = sorted(pages_dir.iterdir()) if pages_dir.exists() else []

        for page_dir in page_dirs:
            if not page_dir.is_dir():
                continue

            page_number = int(page_dir.name)
            process_page(
                repo=repo,
                seo_repo=seo,
                document_id=doc.id,
                page_number=page_number,
                page_dir=page_dir,
            )

        # ── document-level SEO ──
        # aggregate page analysis into document-level metadata
        first_page_info = _load_json(pages_dir / "1" / "info.json")
        if first_page_info is not None:
            first_page_info["image_path"] = str(pages_dir / "1" / "image.png")
            meta = get_meta_info(first_page_info)
            seo.upsert_seo_from_dict(doc.id, meta)
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
) -> None:
    image_path = page_dir / "image.png"
    text_path = page_dir / "text.txt"
    info_path = page_dir / "info.json"

    # ── OCR ──
    page_text = image_to_text(image_path=str(image_path))
    write_to_file(file_path=str(text_path), contents=page_text)

    # ── analysis ──
    analyzed_data = analyze_page(text_path=str(text_path))
    safe_dump_to_json(file_path=str(info_path), data=analyzed_data)

    # ── register page in DB ──
    page = repo.upsert_page(
        document_id=document_id,
        page_number=page_number,
        image_path=str(image_path),
        text_path=str(text_path),
        info_path=str(info_path),
    )

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

    logger.info("  Page %d: OCR + analysis + registered", page_number)


# ── helpers ──


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ── entrypoint ──

if __name__ == "__main__":
    run_pipeline()
