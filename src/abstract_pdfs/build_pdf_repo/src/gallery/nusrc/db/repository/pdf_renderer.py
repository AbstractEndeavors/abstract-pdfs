"""
pdf_renderer.py — Render PDF pages to PNG images and register them.

Dependencies:
    pip install PyMuPDF  (imported as 'fitz')

Design:
  - Renders to a predictable path structure: base_dir/pages/{page_num}/image.png
  - Returns a manifest of what was produced, not side effects.
  - Repository calls are separate from rendering — the caller wires them together.
"""

from __future__ import annotations

import logging,os
from dataclasses import dataclass
from pathlib import Path
from abstract_utilities import safe_load_from_json,read_from_file,get_file_parts,safe_join
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def pad_page_number(n: int, width: int = 4) -> str:
    """Zero-pad a page number: 1 → '001', 12 → '012', 100 → '100'."""
    return str(n).zfill(width)


@dataclass(frozen=True, slots=True)
class RenderedPage:
    page_number: int
    image_path: Path
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class RenderResult:
    pdf_path: Path
    pages: list[RenderedPage]
    total_pages: int
    dpi: int


def render_pdf_pages(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 600,
    fmt: str = "png",
) -> RenderResult:
    """
    Render every page of a PDF to an image file.

    Directory structure created:
        output_dir/
            pages/
                001/
                    image.png
                002/
                    image.png
                ...

    Args:
        pdf_path:   Path to the source PDF.
        output_dir: Base directory for this document.
        dpi:        Resolution. 200 is a good balance of quality vs size.
        fmt:        Output format — 'png' or 'jpeg'.

    Returns:
        RenderResult with a manifest of every rendered page.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    try:
        pages_dir = safe_join(output_dir,"pages")
        doc = fitz.open(str(pdf_path))
        rendered: list[RenderedPage] = []
    except:
        return 
    try:
        zoom = dpi / 72  # PDF base resolution is 72 DPI
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(doc.page_count):
            page_dir = safe_join(pages_dir,pad_page_number(page_num + 1))
            Path(page_dir).mkdir(parents=True, exist_ok=True)
            image_path = safe_join(page_dir,f"image.{fmt}")

            if os.path.exists(image_path) and Path(image_path).stat().st_size > 0:
                # read dimensions from existing file without re-rendering
                existing = fitz.Pixmap(str(image_path))
                rendered.append(RenderedPage(
                    page_number=page_num + 1,
                    image_path=image_path,
                    width=existing.width,
                    height=existing.height,
                ))
                existing = None
##                logger.info(
##                    "Skipped page %d/%d (image exists)",
##                    page_num + 1, doc.page_count,
##                )
                continue

            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(str(image_path))

            rendered.append(RenderedPage(
                page_number=page_num + 1,
                image_path=image_path,
                width=pix.width,
                height=pix.height,
            ))

            logger.info(
                "Rendered page %d/%d → %s (%dx%d)",
                page_num + 1, doc.page_count, image_path, pix.width, pix.height,
            )

        return RenderResult(
            pdf_path=pdf_path,
            pages=rendered,
            total_pages=doc.page_count,
            dpi=dpi,
        )
    finally:
        doc.close()


def render_and_register(
    pdf_path: Path,
    output_dir: Path,
    document_id: int,
    repo,  # Repository instance
    dpi: int = 200,
) -> RenderResult:
    """
    Render all pages, then register each one in the database.

    This is the composition point — rendering is pure IO,
    registration is a repository call. Kept together here
    because they always run as a pair.
    """
    result = render_pdf_pages(pdf_path, output_dir, dpi=dpi)

    repo.update_page_count(document_id, result.total_pages)

    for page in result.pages:
        repo.upsert_page(
            document_id=document_id,
            page_number=page.page_number,
            image_path=str(page.image_path),
        )

    logger.info(
        "Registered %d pages for document %d", result.total_pages, document_id
    )
    return result
