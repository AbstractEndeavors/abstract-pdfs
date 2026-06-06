from .imports import *
from ..documents import *


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
    def from_pipeline_output(cls, keywords: dict[str, Any]):
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
    def from_metadata_dict(cls, meta: dict[str, Any]):
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




