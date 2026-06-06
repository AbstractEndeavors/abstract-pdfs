from .imports import *
from .helpers import *
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


