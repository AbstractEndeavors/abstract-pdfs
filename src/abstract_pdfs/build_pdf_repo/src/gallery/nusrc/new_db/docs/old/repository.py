"""
repository.py — Data access layer for the document registry.

Design decisions:
  - Connection is injected, never acquired internally.
  - Return types are dataclasses, never raw tuples.
  - Every public method is one logical operation, one transaction.
  - No module-level state. Wire a Repository instance at your composition root.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection


# ── Schemas ──────────────────────────────────────────────────


class Status(str, Enum):
    PENDING   = "pending"
    INGESTING = "ingesting"
    ANALYZING = "analyzing"
    COMPLETE  = "complete"
    FAILED    = "failed"


@dataclass(frozen=True, slots=True)
class Tenant:
    id: str
    name: str
    slug: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Document:
    id: int
    tenant_id: str
    doc_id: str
    slug: str
    base_path: str
    pdf_path: str
    status: Status
    page_count: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Page:
    id: int
    document_id: int
    page_number: int
    image_path: str | None
    text_path: str | None
    info_path: str | None
    metadata_path: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PageAnalysis:
    id: int
    page_id: int
    analysis_type: str
    payload: dict[str, Any]
    model_version: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PipelineRun:
    id: int
    document_id: int
    status: Status
    stage: str
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class Tag:
    id: int
    slug: str
    label: str


# ── Identity hashing ────────────────────────────────────────


def identity_hash(slug: str, discriminator: str = "") -> str:
    """Deterministic document ID from stable domain keys."""
    return hashlib.sha256(f"{slug}:{discriminator}".encode()).hexdigest()


# ── Repository ───────────────────────────────────────────────


class Repository:
    """
    All database operations for the document registry.

    Usage:
        conn = psycopg2.connect(dsn)
        repo = Repository(conn)
        doc  = repo.upsert_document(tenant_id, base_dir)
    """

    def __init__(self, conn: PgConnection) -> None:
        self._conn = conn

    # ── helpers ──

    def _cursor(self):
        cur,_ = get_cur_conn()
        return cur
    def _commit(self) -> None:
        self._conn.commit()

    def _rollback(self) -> None:
        self._conn.rollback()

    # ── tenants ──

    def insert_tenant(self, name: str, slug: str) -> Tenant:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO tenants (name, slug)
                VALUES (%s, %s)
                RETURNING *
            """, (name, slug))
            self._commit()
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
            self._commit()
            return _to_document(cur.fetchone())

    def upsert_document(
        self,
        tenant_id: str,
        slug: str,
        base_path: str,
        pdf_path: str,
        discriminator: str = "",
    ) -> Document:
        """Insert or update paths if the document already exists."""
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
            self._commit()
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
            self._commit()
            return _to_document(row)

    def update_page_count(self, document_id: int, page_count: int) -> Document:
        with self._cursor() as cur:
            cur.execute("""
                UPDATE documents SET page_count = %s WHERE id = %s RETURNING *
            """, (page_count, document_id))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"document {document_id} not found")
            self._commit()
            return _to_document(row)

    def relocate_document(
        self, tenant_id: str, doc_id: str, new_base_path: str
    ) -> int:
        """Call the SQL function that rewrites all paths in one transaction."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT relocate_document(%s, %s, %s)",
                (tenant_id, doc_id, new_base_path),
            )
            result = cur.fetchone()
            self._commit()
            # RealDictCursor returns {"relocate_document": <id>}
            return list(result.values())[0]

    def delete_document(self, document_id: int) -> bool:
        """Hard delete. Cascades to pages, analysis, pipeline runs, tags."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE id = %s RETURNING id", (document_id,)
            )
            deleted = cur.fetchone() is not None
            self._commit()
            return deleted

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
            self._commit()
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
            self._commit()
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
        """
        Insert many pages at once.
        Each dict: {page_number, image_path, text_path, info_path, metadata_path}
        Returns the number of rows inserted.
        """
        if not pages:
            return 0
        values = [
            (
                document_id,
                p["page_number"],
                p.get("image_path"),
                p.get("text_path"),
                p.get("info_path"),
                p.get("metadata_path"),
            )
            for p in pages
        ]
        with self._cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO pages
                    (document_id, page_number, image_path, text_path, info_path, metadata_path)
                VALUES %s
                ON CONFLICT (document_id, page_number) DO NOTHING
                """,
                values,
            )
            count = cur.rowcount
            self._commit()
            return count

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
            """, (page_id, analysis_type, psycopg2.extras.Json(payload), model_version))
            self._commit()
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

    def start_pipeline_run(
        self, document_id: int, stage: str
    ) -> PipelineRun:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO pipeline_runs (document_id, status, stage)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (document_id, Status.INGESTING.value, stage))
            self._commit()
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
            self._commit()
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
            self._commit()
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
        """Get or create a tag. Registry pattern — slug is the identity."""
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO tags (slug, label)
                VALUES (%s, %s)
                ON CONFLICT (slug) DO UPDATE SET label = EXCLUDED.label
                RETURNING *
            """, (slug, label))
            self._commit()
            return _to_tag(cur.fetchone())

    def tag_document(self, document_id: int, tag_slug: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id FROM tags WHERE slug = %s", (tag_slug,)
            )
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"tag '{tag_slug}' not in registry")
            cur.execute("""
                INSERT INTO document_tags (document_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (document_id, row["id"]))
            self._commit()

    def untag_document(self, document_id: int, tag_slug: str) -> None:
        with self._cursor() as cur:
            cur.execute("""
                DELETE FROM document_tags
                WHERE document_id = %s
                  AND tag_id = (SELECT id FROM tags WHERE slug = %s)
            """, (document_id, tag_slug))
            self._commit()

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


# ── Row mappers ──────────────────────────────────────────────
# One place to break if the schema changes. Not scattered across methods.


def _to_tenant(row: dict) -> Tenant:
    return Tenant(
        id=str(row["id"]),
        name=row["name"],
        slug=row["slug"],
        created_at=row["created_at"],
    )


def _to_document(row: dict) -> Document:
    return Document(
        id=row["id"],
        tenant_id=str(row["tenant_id"]),
        doc_id=row["doc_id"],
        slug=row["slug"],
        base_path=row["base_path"],
        pdf_path=row["pdf_path"],
        status=Status(row["status"]),
        page_count=row["page_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _to_page(row: dict) -> Page:
    return Page(
        id=row["id"],
        document_id=row["document_id"],
        page_number=row["page_number"],
        image_path=row["image_path"],
        text_path=row["text_path"],
        info_path=row["info_path"],
        metadata_path=row["metadata_path"],
        created_at=row["created_at"],
    )


def _to_analysis(row: dict) -> PageAnalysis:
    return PageAnalysis(
        id=row["id"],
        page_id=row["page_id"],
        analysis_type=row["analysis_type"],
        payload=row["payload"],
        model_version=row["model_version"],
        created_at=row["created_at"],
    )


def _to_run(row: dict) -> PipelineRun:
    return PipelineRun(
        id=row["id"],
        document_id=row["document_id"],
        status=Status(row["status"]),
        stage=row["stage"],
        error_message=row["error_message"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def _to_tag(row: dict) -> Tag:
    return Tag(id=row["id"], slug=row["slug"], label=row["label"])
