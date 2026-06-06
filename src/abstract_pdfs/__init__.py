from .pdf_utils import *
from .imports import *
from .pipeline import *
from .AbstractPDFManager import *
from .abstract_scaffold import *


# ---------------------------------------------------------------------------
# build_pdf_repo — the current per-page pipeline (image → text → info →
# metadata → html, then gallery + viewer).  Exposed lazily because importing it
# pulls heavy optional deps (abstract_hugpy, OCR); `import abstract_pdfs` stays
# light until you actually call one of these.
#
#     from abstract_pdfs import process_pdf
#     process_pdf("/path/to/doc.pdf")            # or process_pdfs([...]) / process_all_pdfs(dir)
# ---------------------------------------------------------------------------
_BUILD_PDF_REPO_EXPORTS = {"process_pdf", "process_pdfs", "process_all_pdfs"}


def __getattr__(name):
    if name in _BUILD_PDF_REPO_EXPORTS:
        from .build_pdf_repo.src.pdf_pipeline import (
            process_pdf,
            process_pdfs,
            process_all_pdfs,
        )
        globals().update(
            process_pdf=process_pdf,
            process_pdfs=process_pdfs,
            process_all_pdfs=process_all_pdfs,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
