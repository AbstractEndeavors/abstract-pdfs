"""
example_usage.py — How to wire the repositories at your composition root.

This is not a runnable script — it's the wiring pattern.
Replace build_metadata() and your pipeline calls with your real code.
"""

import json
import os
from pathlib import Path

import psycopg2

from repository import Repository, Status
from repository_seo import SeoRepository, SeoMetadataPayload


def get_connection():
    return psycopg2.connect(dsn=os.environ["DATABASE_URL"])


def ingest_document(tenant_id: str, base_dir: Path) -> None:
    conn = get_connection()
    try:
        repo = Repository(conn)
        seo  = SeoRepository(conn)

        # ── register document ──
        slug = base_dir.name
        doc = repo.upsert_document(
            tenant_id=tenant_id,
            slug=slug,
            base_path=str(base_dir),
            pdf_path=str(base_dir / "output.pdf"),
        )
        repo.update_document_status(doc.id, Status.INGESTING)

        run = repo.start_pipeline_run(doc.id, stage="ingest")

        try:
            # ── discover and register pages ──
            page_dirs = sorted(base_dir.glob("pages/*/"))
            repo.update_page_count(doc.id, len(page_dirs))

            for i, page_dir in enumerate(page_dirs, start=1):
                page = repo.upsert_page(
                    document_id=doc.id,
                    page_number=i,
                    image_path=_if_exists(page_dir / "image.png"),
                    text_path=_if_exists(page_dir / "text.txt"),
                    info_path=_if_exists(page_dir / "info.json"),
                    metadata_path=_if_exists(page_dir / "metadata.json"),
                )

                # ── ingest page-level analysis ──
                analysis_file = page_dir / "metadata.json"
                if analysis_file.exists():
                    analysis = json.loads(analysis_file.read_text())

                    seo.ingest_page_analysis(
                        page_id=page.id,
                        summary=analysis.get("summary", ""),
                        keywords=analysis.get("keywords", {}),
                        model_version=analysis.get("model_version"),
                    )

            # ── store document-level SEO metadata ──
            # your build_metadata() returns the big dict you showed
            meta_dict = build_metadata(doc, base_dir)
            seo.upsert_seo_from_dict(doc.id, meta_dict)

            # ── tag it ──
            repo.ensure_tag("needs-review", "Needs Review")
            repo.tag_document(doc.id, "needs-review")

            # ── complete ──
            repo.update_document_status(doc.id, Status.COMPLETE)
            repo.complete_pipeline_run(run.id)

        except Exception as exc:
            repo.update_document_status(doc.id, Status.FAILED)
            repo.fail_pipeline_run(run.id, str(exc))
            raise

    finally:
        conn.close()


def query_examples(tenant_id: str, document_id: int) -> None:
    """Showing the read-side patterns."""
    conn = get_connection()
    try:
        repo = Repository(conn)
        seo  = SeoRepository(conn)

        # what pages are missing OCR?
        missing = seo.find_pages_missing_analysis(document_id, "ocr")
        print(f"Pages missing OCR: {missing}")

        # any keyword-stuffed pages?
        stuffed = seo.find_stuffed_pages(document_id)
        for s in stuffed:
            print(f"  Page {s['page_number']}: {s['payload']['flags']}")

        # aggregate keywords across all pages
        kw_summary = seo.get_document_keyword_summary(document_id)
        print(f"Primary keywords: {kw_summary['primary']}")

        # get the full SEO metadata for rendering <head> tags
        seo_record = seo.get_seo(document_id)
        if seo_record:
            print(f"OG title: {seo_record.og.get('title')}")
            print(f"Twitter card: {seo_record.twitter.get('card')}")

        # pipeline history
        history = repo.get_pipeline_history(document_id)
        for run in history:
            print(f"  {run.stage}: {run.status.value} ({run.started_at})")

    finally:
        conn.close()


# ── helpers ──

def _if_exists(path: Path) -> str | None:
    return str(path) if path.exists() else None


def build_metadata(doc, base_dir: Path) -> dict:
    """Placeholder — your actual build_metadata() goes here."""
    raise NotImplementedError("wire your real build_metadata()")
