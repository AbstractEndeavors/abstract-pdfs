#!/usr/bin/env python3
"""
generate_index_db.py — Static HTML generation from the document registry DB.

Walks the filesystem tree for directory structure, queries the DB for content,
and renders through Jinja2 templates. Every directory gets an index.html:
  - Leaf dirs matching a DB document → viewer page
  - Leaf dirs with info.json (no DB match) → image page
  - Branch dirs with children → gallery index

Design:
  - Filesystem provides structure (which directories exist).
  - DB provides content (titles, descriptions, SEO, page data).
  - Jinja2 templates own all HTML. No f-string markup in Python.
  - Templates are loaded from a registry, not discovered at runtime.
  - All config is explicit. No smart defaults.

Usage:
    python generate_index_db.py \\
        --dsn           "postgresql://user:pass@localhost:5432/tdd_docs" \\
        --tenant-slug   default \\
        --root          /srv/media/thedailydialectics/pdfs \\
        --media-root    /srv/media/thedailydialectics \\
        --base-url      https://thedailydialectics.com/pdfs \\
        --site-root     https://thedailydialectics.com

    # Single directory:
    python generate_index_db.py \\
        --dsn           "postgresql://user:pass@localhost:5432/tdd_docs" \\
        --tenant-slug   default \\
        --root          /srv/media/thedailydialectics/pdfs/wipow/a197278 \\
        --media-root    /srv/media/thedailydialectics \\
        --base-url      https://thedailydialectics.com/pdfs/wipow/a197278 \\
        --site-root     https://thedailydialectics.com \\
        --no-recurse --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..repository import Repository, Status
from ..repository_seo import SeoRepository, DocumentSeo

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

SITE_ROOT_DEFAULT = "https://thedailydialectics.com"

SKIP_DIRS = frozenset({
    "text", "pages", "pdf_pages",
    "preprocessed_images", "preprocessed_text",
    "node_modules", ".git", "__pycache__",
})

IMAGE_EXTS = frozenset({".webp", ".jpg", ".jpeg", ".png", ".gif"})


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


# ═══════════════════════════════════════════════════════════════
# Template registry
# ═══════════════════════════════════════════════════════════════


class TemplateRegistry:
    """
    Loads and caches Jinja2 templates from a directory.
    Templates are registered by name, not discovered at runtime.
    """

    KNOWN_TEMPLATES = frozenset({"viewer", "gallery", "image_page"})

    def __init__(self, template_dir: Path) -> None:
        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(default_for_string=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Validate all known templates exist at init time, not render time
        for name in self.KNOWN_TEMPLATES:
            filename = f"{name}.html.j2"
            try:
                self._env.get_template(filename)
            except Exception as exc:
                raise FileNotFoundError(
                    f"Required template '{filename}' not found in {template_dir}"
                ) from exc

    def render(self, template_name: str, **ctx: Any) -> str:
        if template_name not in self.KNOWN_TEMPLATES:
            raise ValueError(
                f"Unknown template '{template_name}'. "
                f"Known: {sorted(self.KNOWN_TEMPLATES)}"
            )
        tmpl = self._env.get_template(f"{template_name}.html.j2")
        return tmpl.render(**ctx)


# ═══════════════════════════════════════════════════════════════
# Text helpers
# ═══════════════════════════════════════════════════════════════


def clean_text(s: str | list, max_len: int = 160) -> str:
    if isinstance(s, list):
        s = str(s[0]) if s else ""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0] + "…"
    return s


def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


def breadcrumbs_html(base_url: str, site_root: str) -> str:
    path_part = base_url.rstrip("/").replace(site_root, "").lstrip("/")
    segments = [s for s in path_part.split("/") if s]
    crumbs = [f'<a href="{site_root}">Home</a>']
    acc = site_root
    for i, seg in enumerate(segments):
        acc += f"/{seg}"
        if i < len(segments) - 1:
            crumbs.append(f'<a href="{acc}/">{humanize(seg)}</a>')
        else:
            crumbs.append(f"<span>{seg}</span>")
    return " › ".join(crumbs)


def read_text_file(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def child_dirs(directory: Path) -> list[Path]:
    return sorted(
        d for d in directory.iterdir()
        if d.is_dir() and d.name not in SKIP_DIRS and not d.name.startswith(".")
    )


def first_image_url(directory: Path, resolver: PathResolver) -> str | None:
    for ext in IMAGE_EXTS:
        for hit in sorted(directory.rglob(f"*{ext}")):
            if hit.is_file():
                url = resolver.to_url(hit)
                if url:
                    return url
    return None


def load_manifest(directory: Path) -> list[dict] | None:
    """Load a manifest file from the directory (filesystem fallback)."""
    for name in [f"{directory.name}_manifest.json", "manifest.json"]:
        p = directory / name
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Bad manifest %s: %s", p, e)
    return None


# ═══════════════════════════════════════════════════════════════
# DB → intermediate shape assembly
# ═══════════════════════════════════════════════════════════════


class DocumentIndex:
    """
    Pre-loaded index of all documents for a tenant, keyed by slug
    and by base_path. Built once, queried many times during the walk.
    """

    def __init__(
        self,
        repo: Repository,
        seo_repo: SeoRepository,
        tenant_id: str,
    ) -> None:
        self._repo = repo
        self._seo_repo = seo_repo
        self._tenant_id = tenant_id

        # Load everything once
        all_docs = repo.list_documents(tenant_id, limit=100_000)
        self._by_slug: dict[str, Any] = {d.slug: d for d in all_docs}
        self._by_base_path: dict[str, Any] = {d.base_path: d for d in all_docs}

    def find_by_dir(self, directory: Path) -> Any | None:
        """Match a filesystem directory to a document, by slug or base_path."""
        # Try slug match first (most common: dir name == document slug)
        doc = self._by_slug.get(directory.name)
        if doc:
            return doc
        # Try base_path match
        return self._by_base_path.get(str(directory))

    def assemble_view(
        self, document_id: int, resolver: PathResolver, base_url: str,
    ) -> DocumentView | None:
        doc = self._repo.get_document(document_id)
        if doc is None:
            return None

        seo: DocumentSeo | None = self._seo_repo.get_seo(document_id)
        if seo is None:
            return None

        db_pages = self._repo.get_pages(document_id)
        page_metas = self._seo_repo.get_all_page_metas(document_id)
        meta_by_index = {i: m for i, m in enumerate(page_metas)}

        tags = [t.label for t in self._repo.get_document_tags(document_id)]

        pages: list[PageView] = []
        for i, pg in enumerate(db_pages):
            meta = meta_by_index.get(i) or {}
            image_url = resolver.to_url_if_exists(pg.image_path)
            text = read_text_file(pg.text_path)
            if not text:
                text = meta.get("longdesc", "") or meta.get("text", "")
            alt = (
                meta.get("alt")
                or meta.get("title")
                or f"{seo.title} — Page {pg.page_number}"
            )
            pages.append(PageView(
                page_number=pg.page_number,
                image_url=image_url,
                text=text,
                alt=alt,
            ))

        pdf_url = resolver.to_url(doc.pdf_path) or doc.pdf_path
        thumbnail = seo.thumbnail_url
        if not thumbnail and pages:
            thumbnail = pages[0].image_url

        return DocumentView(
            document_id=doc.id,
            slug=doc.slug,
            title=seo.title,
            description=seo.description,
            keywords=seo.keywords,
            pdf_url=pdf_url,
            thumbnail_url=thumbnail,
            canonical_url=seo.canonical_url or f"{base_url.rstrip('/')}/",
            tags=tags,
            pages=pages,
        )

    def make_card_for_dir(
        self, directory: Path, href: str, resolver: PathResolver,
    ) -> GalleryCard:
        """
        Build a gallery card for a child directory.
        Tries DB first, then filesystem manifest, then bare directory name.
        """
        doc = self.find_by_dir(directory)
        if doc:
            seo = self._seo_repo.get_seo(doc.id)
            if seo:
                thumb = seo.thumbnail_url
                if not thumb:
                    pages = self._repo.get_pages(doc.id)
                    if pages and pages[0].image_path:
                        thumb = resolver.to_url_if_exists(pages[0].image_path)
                tags = [t.label for t in self._repo.get_document_tags(doc.id)]
                return GalleryCard(
                    title=seo.title,
                    description=clean_text(seo.description, 160),
                    image_url=thumb,
                    href=href,
                    tags=tags,
                    page_count=doc.page_count,
                )

        # Filesystem fallback: manifest
        manifest = load_manifest(directory)
        if manifest:
            first = manifest[0]
            thumb_raw = first.get("social_meta", {}).get("og:image")
            return GalleryCard(
                title=humanize(directory.name),
                description=clean_text(
                    first.get("longdesc")
                    or first.get("caption")
                    or first.get("keywords_str", "").replace(",", " ")
                    or "",
                    160,
                ),
                image_url=thumb_raw,
                href=href,
                tags=[],
                page_count=len(manifest),
            )

        # Filesystem fallback: info.json
        info_path = directory / "info.json"
        if info_path.exists():
            try:
                meta = json.loads(info_path.read_text())
                raw_url = (
                    meta.get("schema", {}).get("url")
                    or meta.get("social_meta", {}).get("og:image")
                )
                return GalleryCard(
                    title=meta.get("title") or humanize(directory.name),
                    description=clean_text(
                        meta.get("longdesc") or meta.get("caption") or "", 160
                    ),
                    image_url=raw_url,
                    href=href,
                    tags=[],
                    page_count=None,
                )
            except (json.JSONDecodeError, OSError):
                pass

        # Bare directory — no metadata available
        return GalleryCard(
            title=humanize(directory.name),
            description="",
            image_url=first_image_url(directory, resolver),
            href=href,
            tags=[],
            page_count=None,
        )


# ═══════════════════════════════════════════════════════════════
# Rendering — templates + context
# ═══════════════════════════════════════════════════════════════


def render_viewer(
    templates: TemplateRegistry,
    view: DocumentView,
    site_root: str,
) -> str:
    pages_js = [
        {
            "n": pv.page_number,
            "thumb": pv.image_url or "",
            "text": pv.text,
            "alt": pv.alt.split(" | ")[0] if pv.alt else f"Page {pv.page_number}",
        }
        for pv in view.pages
    ]
    keywords_list = [
        kw.strip()
        for kw in view.keywords.split(",")
        if kw.strip() and len(kw.strip()) > 2
    ][:12]
    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": view.title,
        "description": clean_text(view.description, 300),
        "keywords": view.keywords,
        "url": view.pdf_url,
        "thumbnailUrl": view.thumbnail_url or "",
        "fileFormat": "application/pdf",
    }

    return templates.render(
        "viewer",
        title=view.title,
        description=clean_text(view.description, 300),
        keywords=view.keywords,
        canonical_url=view.canonical_url,
        first_thumb=pages_js[0]["thumb"] if pages_js else "",
        schema_json=json.dumps(schema, indent=2),
        site_root=site_root,
        total=len(view.pages),
        pdf_url=view.pdf_url,
        pages_json=json.dumps(pages_js, ensure_ascii=False),
        pdf_url_json=json.dumps(view.pdf_url),
        keywords_json=json.dumps(keywords_list),
    )


def render_gallery(
    templates: TemplateRegistry,
    cards: list[GalleryCard],
    title: str,
    base_url: str,
    site_root: str,
) -> str:
    canonical = base_url.rstrip("/") + "/"
    card_dicts = [
        {
            "title": c.title,
            "description": c.description,
            "image_url": c.image_url,
            "href": c.href,
            "tags": c.tags,
            "page_count": c.page_count,
        }
        for c in cards
    ]
    return templates.render(
        "gallery",
        page_title=title,
        canonical_url=canonical,
        breadcrumbs=breadcrumbs_html(base_url, site_root),
        heading=title,
        card_count=len(cards),
        cards=card_dicts,
    )


def render_image_page(
    templates: TemplateRegistry,
    meta: dict[str, Any],
    base_url: str,
    site_root: str,
    directory: Path,
    resolver: PathResolver,
) -> str:
    title = meta.get("title") or humanize(directory.name)
    alt = meta.get("alt") or title
    description = clean_text(
        meta.get("longdesc") or meta.get("caption") or "", 300
    )
    keywords = meta.get("keywords_str", "")
    img_url = (
        meta.get("schema", {}).get("url")
        or meta.get("social_meta", {}).get("og:image")
    )
    # Filesystem fallback for image
    if not img_url:
        img_url = first_image_url(directory, resolver)

    keyword_tags = [kw.strip() for kw in keywords.split(",") if kw.strip()]

    return templates.render(
        "image_page",
        title=title,
        alt=alt,
        description=description,
        keywords=keywords,
        keyword_tags=keyword_tags,
        img_url=img_url,
        og_image=img_url or "",
        schema_json=json.dumps(meta.get("schema", {}), indent=2),
        license=meta.get("license", ""),
        attribution=meta.get("attribution", ""),
        canonical_url=base_url.rstrip("/") + "/",
        breadcrumbs=breadcrumbs_html(base_url, site_root),
    )


# ═══════════════════════════════════════════════════════════════
# Directory walker — the recursive orchestrator
# ═══════════════════════════════════════════════════════════════


@dataclass
class WalkConfig:
    """All the explicit wiring a walk needs."""
    site_root: str
    dry_run: bool
    templates: TemplateRegistry
    resolver: PathResolver
    doc_index: DocumentIndex


def _write_html(path: Path, html: str, label: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] {path}  [{label}]")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        print(f"wrote {path}  [{label}]")


def generate_for_directory(
    directory: Path,
    base_url: str,
    config: WalkConfig,
    recurse: bool = True,
) -> bool:
    """
    Generate index.html for this directory. Returns True if something was written.

    Decision order:
      1. Does this dir match a DB document with SEO? → viewer page
      2. Does this dir have a filesystem manifest?   → viewer page (filesystem fallback)
      3. Does this dir have info.json?               → image page
      4. Does this dir have children?                → gallery page
      5. Otherwise                                   → skip
    """
    out_file = directory / "index.html"

    # ── 1. DB document match → viewer page ──
    doc = config.doc_index.find_by_dir(directory)
    if doc:
        view = config.doc_index.assemble_view(
            doc.id, config.resolver, base_url
        )
        if view and view.pages:
            html = render_viewer(config.templates, view, config.site_root)
            _write_html(out_file, html, f"viewer, {len(view.pages)} pages", config.dry_run)
            # Viewer pages are leaves — don't recurse into their subdirs
            return True

    # ── 2. Filesystem manifest (not yet in DB) → viewer page ──
    # Preserves v5 behavior for dirs that haven't been ingested yet
    manifest = load_manifest(directory)
    if manifest:
        html = _render_manifest_viewer(
            directory, base_url, manifest, config
        )
        _write_html(out_file, html, f"viewer/manifest, {len(manifest)} pages", config.dry_run)
        return True

    # ── 3. info.json → image page ──
    info_path = directory / "info.json"
    if info_path.exists():
        try:
            meta = json.loads(info_path.read_text())
            html = render_image_page(
                config.templates, meta, base_url,
                config.site_root, directory, config.resolver,
            )
            _write_html(out_file, html, "image page", config.dry_run)
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Bad info.json %s: %s", info_path, e)

    # ── 4. Branch dir with children → gallery ──
    children = child_dirs(directory)
    if not children:
        return False

    # Recurse first so child pages exist before we build the gallery
    if recurse:
        for child in children:
            child_url = f"{base_url.rstrip('/')}/{child.name}"
            generate_for_directory(child, child_url, config, recurse=True)

    # Build gallery cards for immediate children
    cards = [
        config.doc_index.make_card_for_dir(
            child,
            href=f"{base_url.rstrip('/')}/{child.name}/",
            resolver=config.resolver,
        )
        for child in children
    ]

    html = render_gallery(
        config.templates, cards, humanize(directory.name),
        base_url, config.site_root,
    )
    _write_html(out_file, html, f"gallery, {len(cards)} cards", config.dry_run)
    return True


def _render_manifest_viewer(
    directory: Path,
    base_url: str,
    manifest: list[dict],
    config: WalkConfig,
) -> str:
    """
    Render a viewer page from a filesystem manifest (not yet in DB).
    This is the backward-compat path for dirs that haven't been ingested.
    Uses the same viewer template, just assembles context differently.
    """
    title = humanize(directory.name)
    first = manifest[0]
    description = clean_text(
        first.get("longdesc") or first.get("caption") or "", 300
    )
    keywords_raw = set()
    for entry in manifest:
        for kw in entry.get("keywords_str", "").split(","):
            kw = kw.strip()
            if kw and len(kw) > 2:
                keywords_raw.add(kw)
    keywords = ", ".join(sorted(keywords_raw)[:30])
    keywords_list = sorted(keywords_raw)[:12]

    pages_js = []
    for i, entry in enumerate(manifest, 1):
        thumb = entry.get("social_meta", {}).get("og:image")
        pages_js.append({
            "n": i,
            "thumb": thumb or "",
            "text": entry.get("longdesc", "").strip(),
            "alt": entry.get("alt", "").split(" | ")[0] or f"Page {i}",
        })

    pdf_url = first.get("schema", {}).get("url", "")
    first_thumb = pages_js[0]["thumb"] if pages_js else ""

    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "description": description,
        "keywords": keywords,
        "url": pdf_url,
        "thumbnailUrl": first_thumb,
        "fileFormat": "application/pdf",
    }

    return config.templates.render(
        "viewer",
        title=title,
        description=description,
        keywords=keywords,
        canonical_url=base_url.rstrip("/") + "/",
        first_thumb=first_thumb,
        schema_json=json.dumps(schema, indent=2),
        site_root=config.site_root,
        total=len(pages_js),
        pdf_url=pdf_url,
        pages_json=json.dumps(pages_js, ensure_ascii=False),
        pdf_url_json=json.dumps(pdf_url),
        keywords_json=json.dumps(keywords_list),
    )


# ═══════════════════════════════════════════════════════════════
# Entry point — wires everything, then walks
# ═══════════════════════════════════════════════════════════════


@dataclass
class CLIConfig:
    dsn: str
    tenant_slug: str
    root: Path
    media_root: Path
    base_url: str
    site_root: str
    template_dir: Path
    no_recurse: bool
    dry_run: bool


def run(cfg: CLIConfig) -> None:
    conn = psycopg.connect(cfg.dsn, autocommit=True)
    try:
        repo = Repository(conn)
        seo_repo = SeoRepository(conn)

        tenant = repo.get_tenant_by_slug(cfg.tenant_slug)
        if tenant is None:
            print(f"ERROR: no tenant with slug={cfg.tenant_slug!r}", file=sys.stderr)
            sys.exit(1)

        templates = TemplateRegistry(cfg.template_dir)
        resolver = PathResolver(media_root=cfg.media_root, site_root=cfg.site_root)
        doc_index = DocumentIndex(repo, seo_repo, tenant.id)

        walk_config = WalkConfig(
            site_root=cfg.site_root,
            dry_run=cfg.dry_run,
            templates=templates,
            resolver=resolver,
            doc_index=doc_index,
        )

        generate_for_directory(
            directory=cfg.root,
            base_url=cfg.base_url,
            config=walk_config,
            recurse=not cfg.no_recurse,
        )
    finally:
        conn.close()


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate static HTML for every directory from the document registry DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dsn",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL DSN (or set DATABASE_URL env var)",
    )
    p.add_argument("--tenant-slug", required=True, dest="tenant_slug")
    p.add_argument(
        "--root", required=True,
        help="Filesystem root to walk (e.g. /srv/media/thedailydialectics/pdfs)",
    )
    p.add_argument(
        "--media-root", required=True, dest="media_root",
        help="Top-level media root for path→URL conversion",
    )
    p.add_argument(
        "--base-url", required=True, dest="base_url",
        help="Public URL for --root (e.g. https://thedailydialectics.com/pdfs)",
    )
    p.add_argument(
        "--site-root",
        default=SITE_ROOT_DEFAULT, dest="site_root",
    )
    p.add_argument(
        "--template-dir",
        default=None, dest="template_dir",
        help="Path to Jinja2 templates (default: ./templates/ next to this script)",
    )
    p.add_argument("--no-recurse", action="store_true", dest="no_recurse")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    args = p.parse_args()

    if not args.dsn:
        print("ERROR: --dsn or DATABASE_URL required", file=sys.stderr)
        sys.exit(1)

    template_dir = Path(args.template_dir) if args.template_dir else (
        Path(__file__).resolve().parent / "templates"
    )

    cfg = CLIConfig(
        dsn=args.dsn,
        tenant_slug=args.tenant_slug,
        root=Path(args.root).resolve(),
        media_root=Path(args.media_root).resolve(),
        base_url=args.base_url.rstrip("/"),
        site_root=args.site_root.rstrip("/"),
        template_dir=template_dir,
        no_recurse=args.no_recurse,
        dry_run=args.dry_run,
    )

    if not cfg.root.is_dir():
        print(f"ERROR: {cfg.root} is not a directory", file=sys.stderr)
        sys.exit(1)

    run(cfg)


if __name__ == "__main__":
    main()
