"""
repository.py — Data access layer for the document registry.

Uses psycopg 3 (import psycopg, not psycopg2).

Design decisions:
  - Connection is injected, never acquired internally.
  - Return types are dataclasses, never raw tuples.
  - Every public method is one logical operation.
  - Connection should be created with autocommit=True.
  - No module-level state. Wire a Repository instance at your composition root.
"""




# ── Repository ───────────────────────────────────────────────
from .imports import *
from .classes import *
from .row_mappers import (
    _to_page,
    _to_analysis,
    _to_run,
    _to_tag,
    _to_document,
    _to_tenant
    )
class Repository:
    """
    All database operations for the document registry.

    Usage:
        conn = psycopg.connect(dsn, autocommit=True)
        repo = Repository(conn)
        doc  = repo.upsert_document(tenant_id, base_dir)
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def _cursor(self):
        return self._conn.cursor(row_factory=dict_row)

    # ── tenants ──

    def insert_tenant(self, name: str, slug: str) -> Tenant:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO tenants (name, slug)
                VALUES (%s, %s)
                RETURNING *
            """, (name, slug))
            return _to_tenant(cur.fetchone())

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM tenants WHERE id = %s", (tenant_id,))
            row = cur.fetchone()
            return _to_tenant(row) if row else None

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM tenants WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return _to_tenant(row) if row else None

    # ── documents ──

    def insert_document(
        self,
        tenant_id: str,
        slug: str,
        base_path: str,
        pdf_path: str,
        discriminator: str = "",
    ) -> Document:
        doc_id = identity_hash(slug, discriminator)
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO documents (tenant_id, doc_id, slug, base_path, pdf_path)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (tenant_id, doc_id, slug, base_path, pdf_path))
            return _to_document(cur.fetchone())

    def upsert_document(
        self,
        tenant_id: str,
        slug: str,
        base_path: str,
        pdf_path: str,
        discriminator: str = "",
    ) -> Document:
        doc_id = identity_hash(slug, discriminator)
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO documents (tenant_id, doc_id, slug, base_path, pdf_path)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, doc_id) DO UPDATE
                    SET base_path  = EXCLUDED.base_path,
                        pdf_path   = EXCLUDED.pdf_path,
                        updated_at = now()
                RETURNING *
            """, (tenant_id, doc_id, slug, base_path, pdf_path))
            return _to_document(cur.fetchone())

    def get_document(self, document_id: int) -> Document | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
            row = cur.fetchone()
            return _to_document(row) if row else None

    def get_document_by_hash(self, tenant_id: str, doc_id: str) -> Document | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM documents WHERE tenant_id = %s AND doc_id = %s",
                (tenant_id, doc_id),
            )
            row = cur.fetchone()
            return _to_document(row) if row else None

    def list_documents(
        self,
        tenant_id: str,
        status: Status | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        clauses = ["tenant_id = %s"]
        params: list[Any] = [tenant_id]
        if status is not None:
            clauses.append("status = %s")
            params.append(status.value)
        params.extend([limit, offset])

        with self._cursor() as cur:
            cur.execute(f"""
                SELECT * FROM documents
                WHERE {" AND ".join(clauses)}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, params)
            return [_to_document(r) for r in cur.fetchall()]

    def update_document_status(self, document_id: int, status: Status) -> Document:
        with self._cursor() as cur:
            cur.execute("""
                UPDATE documents SET status = %s WHERE id = %s RETURNING *
            """, (status.value, document_id))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"document {document_id} not found")
            return _to_document(row)

    def update_page_count(self, document_id: int, page_count: int) -> Document:
        with self._cursor() as cur:
            cur.execute("""
                UPDATE documents SET page_count = %s WHERE id = %s RETURNING *
            """, (page_count, document_id))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"document {document_id} not found")
            return _to_document(row)

    def relocate_document(
        self, tenant_id: str, doc_id: str, new_base_path: str
    ) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT relocate_document(%s, %s, %s)",
                (tenant_id, doc_id, new_base_path),
            )
            row = cur.fetchone()
            return list(row.values())[0]

    def delete_document(self, document_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE id = %s RETURNING id", (document_id,)
            )
            return cur.fetchone() is not None

    # ── pages ──

    def insert_page(
        self,
        document_id: int,
        page_number: int,
        image_path: str | None = None,
        text_path: str | None = None,
        info_path: str | None = None,
        metadata_path: str | None = None,
    ) -> Page:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO pages
                    (document_id, page_number, image_path, text_path, info_path, metadata_path)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (document_id, page_number, image_path, text_path, info_path, metadata_path))
            return _to_page(cur.fetchone())

    def upsert_page(
        self,
        document_id: int,
        page_number: int,
        image_path: str | None = None,
        text_path: str | None = None,
        info_path: str | None = None,
        metadata_path: str | None = None,
    ) -> Page:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO pages
                    (document_id, page_number, image_path, text_path, info_path, metadata_path)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id, page_number) DO UPDATE
                    SET image_path    = COALESCE(EXCLUDED.image_path,    pages.image_path),
                        text_path     = COALESCE(EXCLUDED.text_path,     pages.text_path),
                        info_path     = COALESCE(EXCLUDED.info_path,     pages.info_path),
                        metadata_path = COALESCE(EXCLUDED.metadata_path, pages.metadata_path)
                RETURNING *
            """, (document_id, page_number, image_path, text_path, info_path, metadata_path))
            return _to_page(cur.fetchone())

    def get_pages(self, document_id: int) -> list[Page]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM pages
                WHERE document_id = %s
                ORDER BY page_number
            """, (document_id,))
            return [_to_page(r) for r in cur.fetchall()]

    def bulk_insert_pages(self, document_id: int, pages: list[dict]) -> int:
        if not pages:
            return 0
        with self._cursor() as cur:
            cur.executemany(
                """
                INSERT INTO pages
                    (document_id, page_number, image_path, text_path, info_path, metadata_path)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id, page_number) DO NOTHING
                """,
                [
                    (
                        document_id,
                        p["page_number"],
                        p.get("image_path"),
                        p.get("text_path"),
                        p.get("info_path"),
                        p.get("metadata_path"),
                    )
                    for p in pages
                ],
            )
            return cur.rowcount

    # ── page analysis ──

    def upsert_analysis(
        self,
        page_id: int,
        analysis_type: str,
        payload: dict[str, Any],
        model_version: str | None = None,
    ) -> PageAnalysis:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO page_analysis (page_id, analysis_type, payload, model_version)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (page_id, analysis_type) DO UPDATE
                    SET payload       = EXCLUDED.payload,
                        model_version = EXCLUDED.model_version,
                        created_at    = now()
                RETURNING *
            """, (page_id, analysis_type, Jsonb(payload), model_version))
            return _to_analysis(cur.fetchone())

    def get_analysis(self, page_id: int, analysis_type: str) -> PageAnalysis | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM page_analysis WHERE page_id = %s AND analysis_type = %s",
                (page_id, analysis_type),
            )
            row = cur.fetchone()
            return _to_analysis(row) if row else None

    def get_all_analysis(self, page_id: int) -> list[PageAnalysis]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM page_analysis WHERE page_id = %s ORDER BY analysis_type",
                (page_id,),
            )
            return [_to_analysis(r) for r in cur.fetchall()]

    # ── pipeline runs ──

    def start_pipeline_run(self, document_id: int, stage: str) -> PipelineRun:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO pipeline_runs (document_id, status, stage)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (document_id, Status.INGESTING.value, stage))
            return _to_run(cur.fetchone())

    def complete_pipeline_run(self, run_id: int) -> PipelineRun:
        with self._cursor() as cur:
            cur.execute("""
                UPDATE pipeline_runs
                SET status = %s, finished_at = now()
                WHERE id = %s
                RETURNING *
            """, (Status.COMPLETE.value, run_id))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"pipeline run {run_id} not found")
            return _to_run(row)

    def fail_pipeline_run(self, run_id: int, error: str) -> PipelineRun:
        with self._cursor() as cur:
            cur.execute("""
                UPDATE pipeline_runs
                SET status = %s, error_message = %s, finished_at = now()
                WHERE id = %s
                RETURNING *
            """, (Status.FAILED.value, error, run_id))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"pipeline run {run_id} not found")
            return _to_run(row)

    def get_pipeline_history(self, document_id: int) -> list[PipelineRun]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM pipeline_runs
                WHERE document_id = %s
                ORDER BY started_at DESC
            """, (document_id,))
            return [_to_run(r) for r in cur.fetchall()]

    # ── tags ──

    def ensure_tag(self, slug: str, label: str) -> Tag:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO tags (slug, label)
                VALUES (%s, %s)
                ON CONFLICT (slug) DO UPDATE SET label = EXCLUDED.label
                RETURNING *
            """, (slug, label))
            return _to_tag(cur.fetchone())

    def tag_document(self, document_id: int, tag_slug: str) -> None:
        with self._cursor() as cur:
            cur.execute("SELECT id FROM tags WHERE slug = %s", (tag_slug,))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"tag '{tag_slug}' not in registry")
            cur.execute("""
                INSERT INTO document_tags (document_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (document_id, row["id"]))

    def untag_document(self, document_id: int, tag_slug: str) -> None:
        with self._cursor() as cur:
            cur.execute("""
                DELETE FROM document_tags
                WHERE document_id = %s
                  AND tag_id = (SELECT id FROM tags WHERE slug = %s)
            """, (document_id, tag_slug))

    def get_document_tags(self, document_id: int) -> list[Tag]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT t.* FROM tags t
                JOIN document_tags dt ON dt.tag_id = t.id
                WHERE dt.document_id = %s
                ORDER BY t.slug
            """, (document_id,))
            return [_to_tag(r) for r in cur.fetchall()]

    def list_documents_by_tag(
        self, tenant_id: str, tag_slug: str
    ) -> list[Document]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT d.* FROM documents d
                JOIN document_tags dt ON dt.document_id = d.id
                JOIN tags t ON t.id = dt.tag_id
                WHERE d.tenant_id = %s AND t.slug = %s
                ORDER BY d.created_at DESC
            """, (tenant_id, tag_slug))
            return [_to_document(r) for r in cur.fetchall()]

    def update_page_ocr_status(self, page_id: int, ocr_processed: bool) -> Page:
            """Mark a page as OCR processed (or not)."""
            with self._cursor() as cur:
                cur.execute("""
                    UPDATE pages SET ocr_processed = %s WHERE id = %s RETURNING *
                """, (ocr_processed, page_id))
                row = cur.fetchone()
                if row is None:
                    raise LookupError(f"page {page_id} not found")
                return _to_page(row)

    def get_pages_needing_ocr(self, document_id: int) -> list[Page]:
        """Get all pages where ocr_processed = False."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM pages
                WHERE document_id = %s AND ocr_processed = False
                ORDER BY page_number
            """, (document_id,))
            return [_to_page(r) for r in cur.fetchall()]
    def save_page_content(
        self,
        page_id: int,
        text_content: str,
        analysis: dict,
        metadata: dict,
    ) -> Page:
        """Save page with explicit analysis and metadata schemas."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE pages SET 
                    text_content = %s,
                    analysis = %s,
                    metadata = %s,
                    ocr_processed = TRUE
                WHERE id = %s
                RETURNING *
            """, (
                text_content,
                Jsonb(analysis),
                Jsonb(metadata),
                page_id
            ))
            return _to_page(cur.fetchone())

    def get_page_content(self, page_id: int) -> dict | None:
        """Get page with typed analysis and metadata."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT id, page_number, text_content, analysis, metadata, ocr_processed
                FROM pages WHERE id = %s
            """, (page_id,))
            return cur.fetchone()
    def ensure_document_pages(self, document_id: int, page_count: int) -> list[Page]:
        """Create page records for all pages in a document if they don't exist."""
        with self._cursor() as cur:
            # Get existing pages
            cur.execute("""
                SELECT page_number FROM pages WHERE document_id = %s
            """, (document_id,))
            existing = {row['page_number'] for row in cur.fetchall()}
            
            # Create missing pages
            pages_to_create = [
                (document_id, i, None, None, None, None)
                for i in range(1, page_count + 1)
                if i not in existing
            ]
            
            if pages_to_create:
                cur.executemany("""
                    INSERT INTO pages
                        (document_id, page_number, image_path, text_path, info_path, metadata_path)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, pages_to_create)
            
            # Return all pages for this document
            cur.execute("""
                SELECT * FROM pages WHERE document_id = %s ORDER BY page_number
            """, (document_id,))
            return [_to_page(r) for r in cur.fetchall()]
    def mark_page_complete(self, page_id: int) -> Page:
        """Mark a page as fully processed."""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE pages SET page_complete = TRUE WHERE id = %s RETURNING *
            """, (page_id,))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"page {page_id} not found")
            return _to_page(row)

    def get_incomplete_pages(self, document_id: int) -> list[Page]:
        """Get all pages where page_complete = False."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM pages
                WHERE document_id = %s AND page_complete = FALSE
                ORDER BY page_number
            """, (document_id,))
            return [_to_page(r) for r in cur.fetchall()]
    def delete_page(self, page_id: int) -> bool:
        """Delete a page record."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM pages WHERE id = %s RETURNING id", (page_id,))
            return cur.fetchone() is not None

    def delete_document(self, document_id: int) -> int:
        """Delete a document and all its pages. Returns count deleted."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM pages WHERE document_id = %s", (document_id,))
            pages_deleted = cur.rowcount
            
            cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
            
            return pages_deleted
    def rename_document_paths(
        self,
        old_name: str,
        new_name: str,
        tenant_id: str | None = None,
    ) -> dict[str, int]:
        """
        Replace old_name with new_name in all path/slug fields.
        Returns counts of affected rows per table.
        """
        results = {}

        with self._cursor() as cur:
            # ── documents ──
            clause = "tenant_id = %s AND " if tenant_id else ""
            params_base = [tenant_id] if tenant_id else []

            cur.execute(f"""
                UPDATE documents SET
                    slug      = replace(slug,      %s, %s),
                    base_path = replace(base_path, %s, %s),
                    pdf_path  = replace(pdf_path,  %s, %s),
                    updated_at = now()
                WHERE {clause}(
                    slug      LIKE %s OR
                    base_path LIKE %s OR
                    pdf_path  LIKE %s
                )
                RETURNING id
            """, [
                *params_base,
                old_name, new_name,
                old_name, new_name,
                old_name, new_name,
                f"%{old_name}%", f"%{old_name}%", f"%{old_name}%",
            ])
            results["documents"] = cur.rowcount

            # ── pages ──
            cur.execute("""
                UPDATE pages SET
                    image_path    = replace(image_path,    %s, %s),
                    text_path     = replace(text_path,     %s, %s),
                    info_path     = replace(info_path,     %s, %s),
                    metadata_path = replace(metadata_path, %s, %s)
                WHERE
                    image_path    LIKE %s OR
                    text_path     LIKE %s OR
                    info_path     LIKE %s OR
                    metadata_path LIKE %s
            """, [
                old_name, new_name,
                old_name, new_name,
                old_name, new_name,
                old_name, new_name,
                f"%{old_name}%", f"%{old_name}%",
                f"%{old_name}%", f"%{old_name}%",
            ])
            results["pages"] = cur.rowcount

        return results
