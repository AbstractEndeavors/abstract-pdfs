from .classes import *
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
