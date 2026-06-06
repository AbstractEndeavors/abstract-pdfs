from .imports import *
# ═══════════════════════════════════════════════════════════════
# Intermediate shapes
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class PageView:
    page_number: int
    image_url: str | None
    text: str
    alt: str


@dataclass(frozen=True, slots=True)
class DocumentView:
    document_id: int
    slug: str
    title: str
    description: str
    keywords: str
    pdf_url: str
    thumbnail_url: str | None
    canonical_url: str
    tags: list[str]
    pages: list[PageView]


@dataclass(frozen=True, slots=True)
class GalleryCard:
    title: str
    description: str
    image_url: str | None
    href: str
    tags: list[str]
    page_count: int | None


@dataclass(frozen=True, slots=True)
class ImagePageView:
    title: str
    alt: str
    description: str
    keywords: str
    keyword_tags: list[str]
    img_url: str | None
    og_image: str
    schema_json: str
    license: str
    attribution: str
    canonical_url: str
    breadcrumbs: str


# ═══════════════════════════════════════════════════════════════
# Path ↔ URL resolution
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class PathResolver:
    media_root: Path
    site_root: str

    def to_url(self, path: str | Path) -> str | None:
        p = Path(path)
        if not p.is_absolute():
            return None
        try:
            return f"{self.site_root}/{p.relative_to(self.media_root)}"
        except ValueError:
            return None

    def to_url_if_exists(self, path: str | Path | None) -> str | None:
        if path is None:
            return None
        p = Path(path)
        if p.exists():
            return self.to_url(p)
        return None
