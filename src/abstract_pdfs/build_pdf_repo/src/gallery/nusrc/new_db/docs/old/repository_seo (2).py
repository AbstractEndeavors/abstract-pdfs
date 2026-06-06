"""
repository_seo.py — Extensions for SEO metadata and structured page analysis.

Uses psycopg 3.

Depends on: repository.py (base Repository class and schemas)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from repository import PageAnalysis, _to_analysis


# ── SEO Schemas ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DocumentSeo:
    id: int
    document_id: int
    title: str
    description: str
    keywords: str
    canonical_url: str | None
    thumbnail_url: str | None
    og: dict[str, Any]
    twitter: dict[str, Any]
    meta_other: dict[str, Any]
    robots: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisType:
    slug: str
    label: str
    description: str | None


# ── Page analysis payload schemas ────────────────────────────


@dataclass(slots=True)
class KeywordAnalysisPayload:
    """Validated shape for page_analysis.payload when type='keywords'."""
    primary: list[str]
    secondary: list[str]
    hashtags: list[str]
    dropped: list[str]
    preset_used: str
    slug_candidates: list[str]
    meta_keywords: str
    density: dict[str, float]
    density_flags: dict[str, str]
    raw: dict[str, Any]

    @classmethod
    def from_pipeline_output(cls, keywords: dict[str, Any]) -> KeywordAnalysisPayload:
        return cls(
            primary=keywords["primary"],
            secondary=keywords["secondary"],
            hashtags=keywords["hashtags"],
            dropped=keywords["dropped"],
            preset_used=keywords["preset_used"],
            slug_candidates=keywords["slug_candidates"],
            meta_keywords=keywords["meta_keywords"],
            density=keywords["density"],
            density_flags=keywords["density_flags"],
            raw=keywords["raw"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "hashtags": self.hashtags,
            "dropped": self.dropped,
            "preset_used": self.preset_used,
            "slug_candidates": self.slug_candidates,
            "meta_keywords": self.meta_keywords,
            "density": self.density,
            "density_flags": self.density_flags,
            "raw": self.raw,
        }


@dataclass(slots=True)
class SeoMetadataPayload:
    """Validated shape for the SEO metadata dict."""
    title: str
    description: str
    keywords: str
    canonical_url: str | None
    thumbnail_url: str | None
    og: dict[str, Any]
    twitter: dict[str, Any]
    meta_other: dict[str, Any]
    robots: str

    @classmethod
    def from_metadata_dict(cls, meta: dict[str, Any]) -> SeoMetadataPayload:
        other = dict(meta.get("other", {}))
        robots = other.pop("robots", "index, follow")
        return cls(
            title=meta["title"],
            description=meta["description"],
            keywords=meta.get("keywords", ""),
            canonical_url=meta.get("canonical"),
            thumbnail_url=meta.get("thumbnail_url_resized") or meta.get("thumbnail"),
            og=meta.get("og", {}),
            twitter=meta.get("twitter", {}),
            meta_other=other,
            robots=robots,
        )


# ── Extended Repository ──────────────────────────────────────


class SeoRepository:
    """
    SEO and analysis extensions. Wraps the same connection as Repository.

    Usage:
        conn = psycopg.connect(dsn, autocommit=True)
        repo = Repository(conn)
        seo  = SeoRepository(conn)
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def _cursor(self):
        return self._conn.cursor(row_factory=dict_row)

    # ── analysis type registry ──

    def ensure_analysis_type(
        self, slug: str, label: str, description: str | None = None
    ) -> AnalysisType:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO analysis_types (slug, label, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                    SET label = EXCLUDED.label,
                        description = EXCLUDED.description
                RETURNING *
            """, (slug, label, description))
            row = cur.fetchone()
            return AnalysisType(
                slug=row["slug"], label=row["label"], description=row["description"]
            )

    def list_analysis_types(self) -> list[AnalysisType]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM analysis_types ORDER BY slug")
            return [
                AnalysisType(slug=r["slug"], label=r["label"], description=r["description"])
                for r in cur.fetchall()
            ]

    # ── structured page analysis ingestion ──

    def ingest_page_analysis(
        self,
        page_id: int,
        summary: str,
        keywords: dict[str, Any],
        model_version: str | None = None,
    ) -> dict[str, PageAnalysis]:
        """
        Ingest one page's full analysis output.
        Splits into separate analysis records by type.
        """
        kw_payload = KeywordAnalysisPayload.from_pipeline_output(keywords)
        results: dict[str, PageAnalysis] = {}

        with self._cursor() as cur:
            # summary
            cur.execute("""
                INSERT INTO page_analysis (page_id, analysis_type, payload, model_version)
                VALUES (%s, 'summary', %s, %s)
                ON CONFLICT (page_id, analysis_type) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        model_version = EXCLUDED.model_version,
                        created_at = now()
                RETURNING *
            """, (page_id, Jsonb({"text": summary}), model_version))
            results["summary"] = _to_analysis(cur.fetchone())

            # full keyword analysis
            cur.execute("""
                INSERT INTO page_analysis (page_id, analysis_type, payload, model_version)
                VALUES (%s, 'keywords', %s, %s)
                ON CONFLICT (page_id, analysis_type) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        model_version = EXCLUDED.model_version,
                        created_at = now()
                RETURNING *
            """, (page_id, Jsonb(kw_payload.to_dict()), model_version))
            results["keywords"] = _to_analysis(cur.fetchone())

            # density as a separate record
            cur.execute("""
                INSERT INTO page_analysis (page_id, analysis_type, payload, model_version)
                VALUES (%s, 'density', %s, %s)
                ON CONFLICT (page_id, analysis_type) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        model_version = EXCLUDED.model_version,
                        created_at = now()
                RETURNING *
            """, (
                page_id,
                Jsonb({
                    "scores": kw_payload.density,
                    "flags": kw_payload.density_flags,
                }),
                model_version,
            ))
            results["density"] = _to_analysis(cur.fetchone())

            # seo-specific keyword classification
            cur.execute("""
                INSERT INTO page_analysis (page_id, analysis_type, payload, model_version)
                VALUES (%s, 'seo_keywords', %s, %s)
                ON CONFLICT (page_id, analysis_type) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        model_version = EXCLUDED.model_version,
                        created_at = now()
                RETURNING *
            """, (
                page_id,
                Jsonb({
                    "primary": kw_payload.primary,
                    "secondary": kw_payload.secondary,
                    "hashtags": kw_payload.hashtags,
                    "meta_keywords": kw_payload.meta_keywords,
                    "slug_candidates": kw_payload.slug_candidates,
                }),
                model_version,
            ))
            results["seo_keywords"] = _to_analysis(cur.fetchone())

            return results

    # ── document-level SEO metadata ──

    def upsert_seo(
        self, document_id: int, payload: SeoMetadataPayload
    ) -> DocumentSeo:
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO document_seo (
                    document_id, title, description, keywords,
                    canonical_url, thumbnail_url,
                    og, twitter, meta_other, robots
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE
                    SET title         = EXCLUDED.title,
                        description   = EXCLUDED.description,
                        keywords      = EXCLUDED.keywords,
                        canonical_url = EXCLUDED.canonical_url,
                        thumbnail_url = EXCLUDED.thumbnail_url,
                        og            = EXCLUDED.og,
                        twitter       = EXCLUDED.twitter,
                        meta_other    = EXCLUDED.meta_other,
                        robots        = EXCLUDED.robots,
                        updated_at    = now()
                RETURNING *
            """, (
                document_id,
                payload.title,
                payload.description,
                payload.keywords,
                payload.canonical_url,
                payload.thumbnail_url,
                Jsonb(payload.og),
                Jsonb(payload.twitter),
                Jsonb(payload.meta_other),
                payload.robots,
            ))
            return _to_seo(cur.fetchone())

    def upsert_seo_from_dict(self, document_id: int, meta: dict[str, Any]) -> DocumentSeo:
        payload = SeoMetadataPayload.from_metadata_dict(meta)
        return self.upsert_seo(document_id, payload)

    def get_seo(self, document_id: int) -> DocumentSeo | None:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM document_seo WHERE document_id = %s",
                (document_id,),
            )
            row = cur.fetchone()
            return _to_seo(row) if row else None

    def delete_seo(self, document_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM document_seo WHERE document_id = %s RETURNING id",
                (document_id,),
            )
            return cur.fetchone() is not None

    # ── queries across analysis ──

    def find_pages_missing_analysis(
        self, document_id: int, analysis_type: str
    ) -> list[int]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT p.id FROM pages p
                LEFT JOIN page_analysis pa
                    ON pa.page_id = p.id AND pa.analysis_type = %s
                WHERE p.document_id = %s
                  AND pa.id IS NULL
                ORDER BY p.page_number
            """, (analysis_type, document_id))
            return [r["id"] for r in cur.fetchall()]

    def find_stuffed_pages(self, document_id: int) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT p.page_number, pa.payload
                FROM page_analysis pa
                JOIN pages p ON p.id = pa.page_id
                WHERE p.document_id = %s
                  AND pa.analysis_type = 'density'
                  AND pa.payload -> 'flags' @> '"stuffed"'
                ORDER BY p.page_number
            """, (document_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_document_keyword_summary(
        self, document_id: int
    ) -> dict[str, list[str]]:
        with self._cursor() as cur:
            cur.execute("""
                SELECT
                    array_agg(DISTINCT kw) FILTER (WHERE src = 'primary')   AS primary_kws,
                    array_agg(DISTINCT kw) FILTER (WHERE src = 'secondary') AS secondary_kws,
                    array_agg(DISTINCT kw) FILTER (WHERE src = 'hashtag')   AS hashtags
                FROM (
                    SELECT unnest(
                        ARRAY(SELECT jsonb_array_elements_text(pa.payload -> 'primary'))
                    ) AS kw, 'primary' AS src
                    FROM page_analysis pa
                    JOIN pages p ON p.id = pa.page_id
                    WHERE p.document_id = %s AND pa.analysis_type = 'seo_keywords'

                    UNION ALL

                    SELECT unnest(
                        ARRAY(SELECT jsonb_array_elements_text(pa.payload -> 'secondary'))
                    ), 'secondary'
                    FROM page_analysis pa
                    JOIN pages p ON p.id = pa.page_id
                    WHERE p.document_id = %s AND pa.analysis_type = 'seo_keywords'

                    UNION ALL

                    SELECT unnest(
                        ARRAY(SELECT jsonb_array_elements_text(pa.payload -> 'hashtags'))
                    ), 'hashtag'
                    FROM page_analysis pa
                    JOIN pages p ON p.id = pa.page_id
                    WHERE p.document_id = %s AND pa.analysis_type = 'seo_keywords'
                ) sub
            """, (document_id, document_id, document_id))
            row = cur.fetchone()
            return {
                "primary": row["primary_kws"] or [],
                "secondary": row["secondary_kws"] or [],
                "hashtags": row["hashtags"] or [],
            }


# ── Row mapper ───────────────────────────────────────────────


def _to_seo(row: dict) -> DocumentSeo:
    return DocumentSeo(
        id=row["id"],
        document_id=row["document_id"],
        title=row["title"],
        description=row["description"],
        keywords=row["keywords"],
        canonical_url=row["canonical_url"],
        thumbnail_url=row["thumbnail_url"],
        og=row["og"],
        twitter=row["twitter"],
        meta_other=row["meta_other"],
        robots=row["robots"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
