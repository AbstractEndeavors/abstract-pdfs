# ── Schemas ──────────────────────────────────────────────────
from .imports import *

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
    ocr_processed: bool = False

@dataclass(frozen=True, slots=True)
class PageAnalysis:
    """Explicit schema for page analysis data."""
    keywords: dict  # density, flags, hashtags, primary, secondary, etc.
    scope: str  # "page", "full", etc.
    summary: str
    text: str
    preset_used: str
    raw: dict  # backends_used, combined, etc.

@dataclass(frozen=True, slots=True)
class PageMetadata:
    """Explicit schema for page metadata."""
    title: str
    description: str
    description_html: str
    keywords: str
    thumbnail: str | None
    canonical: str
    mobile_url: str
    og: dict  # type, title, description, image, etc.
    twitter: dict  # card, title, description, etc.
    other: dict  # robots, author, viewport, etc.


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
