from .imports import *
from .document_rename    import rename_collection
from .SliceManager       import SliceManager


class DocumentPipeline:
    """Orchestrate a single PDF: OCR + enriched manifest, then optional rename.

    For a complete content+HTML build in one call, use ``generate_pdf`` below.
    """

    def __init__(self,
                 pdf_path: str,
                 base_dir=None,
                 out_root=None,
                 engines=None,
                 engine_directory=None,
                 visualize=None,
                 root_url=None,
                 media_root=None,
                 pdfs_public_url=None
                 ):
        self.file_parts = normalize_pdf_path(pdf_path)
        self.pdf_path   = self.file_parts.get("file_path")
        self.base_dir   = self.file_parts.get("dirname")
        self.out_root   = out_root or self.base_dir
        self.engines    = engines or ["layout_ocr"]
        # BUG FIX: these previously had trailing commas, turning each attribute
        # into a 1-tuple (e.g. root_url == (None,)) which SliceManager then
        # mis-used.  Plain assignments now.
        self.engine_directory = engine_directory or False
        self.visualize        = visualize
        self.root_url         = root_url
        self.media_root       = media_root
        self.pdfs_public_url  = pdfs_public_url

    def run(self, rename: bool = True) -> Path:
        print("📂 normalised directory:", self.base_dir)

        # OCR + enriched manifest (process_pdf builds the manifest itself).
        slice_mgr = SliceManager(
            pdf_path=self.pdf_path,
            out_root=self.out_root,
            engines=self.engines,
            engine_directory=self.engine_directory,
            visualize=self.visualize,
            root_url=self.root_url,
            media_root=self.media_root,
            pdfs_public_url=self.pdfs_public_url
            )
        # BUG FIX: was process_pdf(self.engines) — `engines` got passed into the
        # `manifest` parameter.  process_pdf already iterates self.engines.
        self.file_parts = slice_mgr.process_pdf()
        self.pdf_path   = self.file_parts.get("file_path")
        self.base_dir   = self.file_parts.get("dirname")
        self.dirbase    = self.file_parts.get("dirbase")

        if not rename:
            return Path(self.base_dir)

        # Slug rename — collision-tolerant (see rename_collection); a clash no
        # longer aborts the run.  (Removed a call to an undefined
        # `validate_collection` that would have raised NameError.)
        slug    = slugify(self.dirbase)
        new_dir = rename_collection(self.base_dir, slug)

        print("📦 renamed collection:", new_dir)
        return new_dir


# ---------------------------------------------------------------------------
# One-call end-to-end: content (images + OCR + enriched manifest) + HTML.
# ---------------------------------------------------------------------------

def generate_pdf(
    pdf_path: str,
    *,
    engines="layout_ocr",
    media_root=None,
    root_url=None,
    site_root=None,
    pdfs_public_url=None,
    out_root=None,
    enrich: bool = True,
    enrich_config=None,
    describe="__unset__",
    generate_html: bool = True,
    recurse_html: bool = False,
    rename: bool = False,
):
    """Build the complete content for one PDF in a single call.

    Stage 1 — slice pages, OCR, and write the enriched per-page ``info.json``
              plus the document-level ``document.json``.
    Stage 2 — (optional) render the viewer ``index.html`` (and parent gallery
              indexes when ``recurse_html``).

    ``enrich_config`` / ``describe`` are passed straight to the enrichment
    layer, so you can pick a provider (``{"mode": "hugpy"}``) or a vision prompt
    (``describe={"mode": "auto", "prompt": "..."}``) without touching env vars.

    Returns a dict of the artefact paths that were produced.
    """
    # Lazy imports keep module import cheap and avoid cycles.
    from ..abstract_scaffold.src.generators import generate_pdf_manifest
    media_root      = media_root      or MEDIA_ROOT_DIR
    root_url        = root_url        or ROOT_URL
    site_root       = site_root       or root_url
    pdfs_public_url = pdfs_public_url or PDFS_PUBLIC_URL

    # --- Stage 1: OCR (defer manifest so we can pass enrich/describe through) -
    mgr = SliceManager(
        pdf_path=pdf_path,
        out_root=out_root,
        engines=engines,
        media_root=media_root,
        root_url=root_url,
        pdfs_public_url=pdfs_public_url,
    )
    mgr.process_pdf(manifest=False)

    entries = generate_pdf_manifest(
        mgr.pdf_path,
        text_root=mgr.text,
        thumb_root=mgr.images,
        base_url=root_url,
        media_root=media_root,
        pdfs_public_url=pdfs_public_url,
        enrich=enrich,
        enrich_config=enrich_config,
        describe=describe,
    )

    result = {
        "pdf_path": mgr.pdf_path,
        "base_dir": mgr.base_dir,
        "pages": len(entries),
        "document_json": os.path.join(mgr.base_dir, "document.json"),
        "index_html": None,
    }

    # --- Stage 2: HTML ------------------------------------------------------
    if generate_html:
        from ..abstract_scaffold.src.generate_htmls.generate import run as generate_site
        # Public URL of this document's directory (media_root -> site_root).
        try:
            rel = os.path.relpath(mgr.base_dir, media_root)
            doc_base_url = site_root.rstrip("/") + "/" + rel.replace("\\", "/")
        except Exception:
            doc_base_url = root_url.rstrip("/") + "/" + os.path.basename(mgr.base_dir)

        generate_site(
            root=mgr.base_dir,
            base_url=doc_base_url,
            media_root=media_root,
            site_root=site_root,
            recurse=recurse_html,
            pdf_path=mgr.pdf_path,
        )
        result["index_html"] = os.path.join(mgr.base_dir, "index.html")

    if rename:
        slug = slugify(get_file_parts(mgr.pdf_path).get("dirbase"))
        result["renamed_dir"] = str(rename_collection(mgr.base_dir, slug))

    return result
