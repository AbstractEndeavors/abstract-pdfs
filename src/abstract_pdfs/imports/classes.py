from .init_imports import *
from .constants import *
# ─────────────────────────────────────────────────────────────────────────────
# Schemas (dataclasses mirror the TypeScript interfaces exactly)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SocialMeta:
    """Mirrors the social_meta field in ImageData / manifest entries."""
    og_image:       str = ""
    og_image_alt:   str = ""
    twitter_card:   str = "summary_large_image"
    twitter_image:  str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "og:image":       self.og_image,
            "og:image:alt":   self.og_image_alt,
            "twitter:card":   self.twitter_card,
            "twitter:image":  self.twitter_image,
        }


@dataclass
class ImageSchema:
    """Mirrors the schema sub-object in ImageData."""
    context:       str = "https://schema.org"
    type:          str = "ImageObject"
    name:          str = ""
    description:   str = ""
    url:           str = ""
    content_url:   str = ""
    width:         int = 0
    height:        int = 0
    license:       str = "CC BY-SA 4.0"
    creator_type:  str = "Organization"
    creator_name:  str = CREATOR_NAME
    date_published: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "@context":      self.context,
            "@type":         self.type,
            "name":          self.name,
            "description":   self.description,
            "url":           self.url,
            "contentUrl":    self.content_url,
            "width":         self.width,
            "height":        self.height,
            "license":       self.license,
            "creator":       {"@type": self.creator_type, "name": self.creator_name},
            "datePublished": self.date_published,
        }


@dataclass
class ImageInfoJson:
    """
    Full schema for {img_dir}/info.json.
    Mirrors the TypeScript ImageData interface.
    """
    page_url:     str = ""
    alt:          str = ""
    caption:      str = ""
    keywords_str: str = ""
    filename:     str = ""
    ext:          str = ""
    title:        str = ""
    dimensions:   dict[str, int] = field(default_factory=lambda: {"width": 0, "height": 0})
    file_size:    float = 0.0       # MB
    license:      str = "CC BY-SA 4.0"
    attribution:  str = ATTRIBUTION
    longdesc:     str = ""
    schema:       dict[str, Any] = field(default_factory=dict)
    social_meta:  dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_url":     self.page_url,
            "alt":          self.alt,
            "caption":      self.caption,
            "keywords_str": self.keywords_str,
            "filename":     self.filename,
            "ext":          self.ext,
            "title":        self.title,
            "dimensions":   self.dimensions,
            "file_size":    self.file_size,
            "license":      self.license,
            "attribution":  self.attribution,
            "longdesc":     self.longdesc,
            "schema":       self.schema,
            "social_meta":  self.social_meta,
        }


@dataclass
class PdfPageManifestEntry:
    """One entry in {pdf_base}_manifest.json. Mirrors existing manifest structure."""
    page_url:     str = ""
    alt:          str = ""
    caption:      str = ""
    keywords_str: str = ""
    filename:     str = ""
    ext:          str = ".png"
    title:        str = ""
    dimensions:   dict[str, int] = field(default_factory=lambda: {"width": 0, "height": 0})
    file_size:    float = 0.0
    license:      str = "CC BY-SA 4.0"
    attribution:  str = ATTRIBUTION
    longdesc:     str = ""
    description:  str = ""
    summary:      str = ""
    ocr_quality:  float = 0.0
    schema:       dict[str, Any] = field(default_factory=dict)
    social_meta:  dict[str, str] = field(default_factory=dict)
    text_path:    str = ""
    image_path:   str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VariablesJson:
    """
    Full schema for {page_dir}/variables.json.
    Mirrors the TypeScript PageData interface.
    """
    BASE_URL:     str = ""
    href:         str = ""
    title:        str = ""
    content_file: str = ""
    description:  str = ""
    share_url:    str = ""
    keywords_str: str = ""
    thumbnail:    str = ""
    thumbnail_alt:     str = ""
    thumbnail_caption: str = ""
    thumbnail_keywords_str: str = ""
    thumbnail_link:    str = ""
    media:        list[dict] = field(default_factory=list)
    images:       dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "BASE_URL":     self.BASE_URL,
            "href":         self.href,
            "title":        self.title,
            "content_file": self.content_file,
            "description":  self.description,
            "share_url":    self.share_url,
            "keywords_str": self.keywords_str,
            "thumbnail":    self.thumbnail,
            "thumbnail_alt": self.thumbnail_alt,
            "thumbnail_caption": self.thumbnail_caption,
            "thumbnail_keywords_str": self.thumbnail_keywords_str,
            "thumbnail_link": self.thumbnail_link,
            "media":        self.media,
            "images":       self.images,
        }


