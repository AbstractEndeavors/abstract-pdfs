from .imports import *
def _detect_page_number(name: str):
    m = PAGE_RE.search(name)
    return int(m.group(1)) if m else None


def _zero_page(num: int, width: int = 3) -> str:
    return f"page_{str(num).zfill(width)}"


def _safe_move(src: Path, dst: Path, *, strict: bool = False) -> bool:
    """Move src→dst.  Returns True on (logical) success.

    Collision policy (the fix for "one outlier usurps the whole directory"):
      * src == dst                → no-op success.
      * dst exists, same content  → treat as already-done success.
      * dst exists, different      → skip and warn (or raise if ``strict``).
    """
    if src == dst:
        return True
    if dst.exists():
        try:
            same = src.exists() and dst.is_file() and src.is_file() and \
                src.stat().st_size == dst.stat().st_size
        except OSError:
            same = False
        if same:
            # Destination already holds an identical file — consider it done.
            return True
        msg = f"Rename collision — destination exists: {dst}"
        if strict:
            raise RuntimeError(msg)
        logger.warning(msg + " (skipping)")
        return False
    shutil.move(str(src), str(dst))
    return True


def rename_collection(directory: str, slug: str, *, strict: bool = False) -> Path:
    """
    Rename every file inside a processed-PDF directory to carry `slug` as prefix,
    then rename the directory itself.

    Conventions:
      - PDF        → {slug}.pdf
      - Images     → {slug}_{page_NNN}{ext}   (zero-padded to 3 digits)
      - Text files → {slug}_{page_NNN}{ext}
      - Files with no page number in their name are left untouched.

    Robustness: by default this is *non-fatal* — a collision on a single file
    (or on the destination directory) is logged and skipped rather than raised,
    so one outlier PDF cannot abort an entire batch.  Pass ``strict=True`` to
    restore hard failures.

    Returns the resulting directory path (the new slug dir when the final move
    succeeds, otherwise the original directory so callers still have a handle).
    """
    directory = Path(directory)
    parent    = directory.parent
    new_dir   = parent / slug

    # Already renamed (idempotent re-run) — nothing to do.
    if new_dir.exists() and new_dir.resolve() == directory.resolve():
        return new_dir

    pdf_file    = None
    image_files = []
    text_files  = []

    for root, _, files in directory.walk() if hasattr(directory, "walk") else _os_walk(directory):
        for f in files:
            p   = Path(root) / f
            ext = p.suffix.lower()
            if ext in PDF_EXTS:
                pdf_file = p
            elif ext in IMAGE_EXTS:
                image_files.append(p)
            elif ext in TEXT_EXTS:
                text_files.append(p)

    if not pdf_file:
        if strict:
            raise RuntimeError(f"No PDF found in: {directory}")
        logger.warning(f"No PDF found in {directory}; leaving directory untouched")
        return directory

    # PDF
    _safe_move(pdf_file, pdf_file.with_name(f"{slug}.pdf"), strict=strict)

    # Images
    for img in sorted(image_files):
        page = _detect_page_number(img.name)
        if page is None:
            continue
        _safe_move(img, img.with_name(f"{slug}_{_zero_page(page)}{img.suffix}"), strict=strict)

    # Text
    for txt in sorted(text_files):
        page = _detect_page_number(txt.name)
        if page is None:
            continue
        _safe_move(txt, txt.with_name(f"{slug}_{_zero_page(page)}{txt.suffix}"), strict=strict)

    # Directory last.  If the slug dir already exists (a prior partial run, or a
    # genuine name clash), don't raise — keep working in the existing directory.
    if new_dir.exists():
        if strict:
            raise RuntimeError(f"Target directory already exists: {new_dir}")
        logger.warning(
            f"Target directory already exists: {new_dir} — keeping files in {directory}"
        )
        return directory

    if _safe_move(directory, new_dir, strict=strict):
        return new_dir
    return directory


# ---------------------------------------------------------------------------
# compat shim for Python < 3.12 (Path.walk not available)
# ---------------------------------------------------------------------------
import os as _os

def _os_walk(directory: Path):
    for root, dirs, files in _os.walk(directory):
        yield root, dirs, files
