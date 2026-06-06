# ── Row mappers ──────────────────────────────────────────────
from .imports import *
from .classes import *
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

def _to_page_ocr(row: dict | None) -> Page | None:
    """Map database row to PageOCR dataclass."""
    if row is None:
        return None
    return PageOCR(
        id=row.get("id"),
        page_id=row.get("page_id"),
        status=OCRStatus(row.get("status", OCRStatus.PENDING.value)),
        text_path=row.get("text_path"),
        error_message=row.get("error_message"),
        attempted_at=row.get("attempted_at"),
        completed_at=row.get("completed_at"),
    )
