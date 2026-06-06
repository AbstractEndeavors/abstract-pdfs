from .imports import *
from .generate_htmls import *
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def assure_pdf_dir(pdf_path):
    path_parts = get_path_parts(pdf_path)
    basename = path_parts.get('basename')
    dirbase = path_parts.get('dirbase')
    dirname = path_parts.get('dirname')
    filename = path_parts.get('filename')
    if dirbase != filename:
        pdf_dir = os.path.join(dirname, filename)
        os.makedirs(pdf_dir, exist_ok=True)
        nupdf_path = os.path.join(pdf_dir, basename)
        if not os.path.isfile(nupdf_path):
            shutil.move(pdf_path, nupdf_path)
    else:
        pdf_dir = dirname
    return pdf_dir


def assure_pdf_path(pdf_path):
    pdf_dir = assure_pdf_dir(pdf_path)
    dir_parts = get_path_parts(pdf_dir)
    filename = dir_parts.get('filename')
    basename = f"{filename}.pdf"
    return os.path.join(pdf_dir, basename)


def assure_pages_dir_from_pdf_path(pdf_path):
    pdf_path = assure_pdf_path(pdf_path)
    pages_dir = get_pages_dir_from_pdf_path(pdf_path)
    os.makedirs(pages_dir, exist_ok=True)
    return pages_dir


def assure_page_dir_from_pdf_path(pdf_path, page_number):
    assure_pages_dir_from_pdf_path(pdf_path)
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    os.makedirs(page_dir, exist_ok=True)
    return page_dir


def assure_image(pdf_path, page_number):
    image_path = get_page_image_path_from_pdf_path(pdf_path, page_number)
    if not os.path.isfile(image_path):
        logger.info(f"extracting image for page {page_number}")
        i = int(page_number)
        for _, image in pdf_to_images(pdf_path, first_page=i, last_page=i):
            image.save(image_path)
    return image_path


def assure_text_from_pdf_path(pdf_path, page_number):
    assure_page_dir_from_pdf_path(pdf_path, page_number)
    image_path = assure_image(pdf_path, page_number)
    text_path = get_page_text_path_from_pdf_path(pdf_path, page_number)

    if image_needs_text(text_path):
        fetch_text_content(pdf_path, page_number)
        info_path = get_page_info_path_from_pdf_path(pdf_path, page_number)
        if os.path.isfile(info_path):
            os.remove(info_path)
        metadata_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
        if os.path.isfile(metadata_path):
            os.remove(metadata_path)
    return read_from_file(text_path)


def assure_info_from_pdf_path(pdf_path, page_number):
    assure_page_dir_from_pdf_path(pdf_path, page_number)
    assure_image(pdf_path, page_number)
    text = assure_text_from_pdf_path(pdf_path, page_number)
    info_path = get_page_info_path_from_pdf_path(pdf_path, page_number)
    if pdf_page_needs_info(info_path):
        logger.info(f"analyzing page {page_number}")
        info = analyze_page(text=text, page_index=page_number)
        safe_dump_to_json(data=info.to_dict(), file_path=info_path)
        metadata_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
        if os.path.isfile(metadata_path):
            os.remove(metadata_path)
    return safe_load_from_json(info_path)


def assure_metadata_from_pdf_path(pdf_path, page_number):
    assure_page_dir_from_pdf_path(pdf_path, page_number)
    assure_image(pdf_path, page_number)
    assure_text_from_pdf_path(pdf_path, page_number)
    assure_info_from_pdf_path(pdf_path, page_number)
    meta_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
    if pdf_page_needs_info(meta_path):
        metadata = get_metadata_info(pdf_path, page_number)
        safe_dump_to_json(file_path=meta_path, data=metadata)
    return safe_load_from_json(meta_path)


def assure_image_html(pdf_path, page_number):
    assure_metadata_from_pdf_path(pdf_path, page_number)
    image_path = assure_image(pdf_path, page_number)
    return get_image_page(image_path)


# ---------------------------------------------------------------------------
# Per-page worker (the unit of work submitted to the pool)
# ---------------------------------------------------------------------------

def _process_single_page(pdf_path, page_number):
    """
    Process one page end-to-end: image → text → info → metadata → html.

    Returns (page_number, None) on success or (page_number, exception) on failure.
    """
    try:
        assure_image_html(pdf_path, page_number)
        return (page_number, None)
    except Exception as exc:
        logger.error(f"page {page_number} failed: {exc}")
        return (page_number, exc)


# ---------------------------------------------------------------------------
# Threaded orchestrator
# ---------------------------------------------------------------------------

def process_pdf(pdf_path, max_workers=4):
    """
    Process every page of a PDF in parallel, then build gallery + viewer.

    max_workers controls the thread pool size:
        - 1  = sequential (useful for debugging)
        - 4  = safe default for mixed I/O + CPU
        - 8+ = good when the bottleneck is network (OCR API, metadata API)

    Returns a dict with 'total', 'ok', and 'failed' (list of (page, exc) tuples).
    """
    pages_dir = assure_pages_dir_from_pdf_path(pdf_path)
    total_pages = get_num_pdf_pages(pdf_path=pdf_path)

    # page numbers are 1-indexed
    page_numbers = list(range(1, total_pages + 1))

    results = {"total": total_pages, "ok": 0, "failed": []}

    # ------------------------------------------------------------------
    # fan-out: each page is independent, safe to parallelize
    # ------------------------------------------------------------------
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_page = {
            pool.submit(_process_single_page, pdf_path, pn): pn
            for pn in page_numbers
        }

        for future in as_completed(future_to_page):
            page_num, exc = future.result()
            if exc is None:
                results["ok"] += 1
                logger.info(f"page {page_num}/{total_pages} done")
            else:
                results["failed"].append((page_num, exc))
                logger.error(f"page {page_num}/{total_pages} failed: {exc}")

    # ------------------------------------------------------------------
    # fan-in: gallery + viewer require all pages to be on disk
    # ------------------------------------------------------------------
    get_gallery_page(pages_dir)
    get_viewer_page(pdf_path)

    if results["failed"]:
        logger.warning(
            f"{len(results['failed'])}/{total_pages} pages failed: "
            + ", ".join(str(pn) for pn, _ in results["failed"])
        )
    else:
        logger.info(f"all {total_pages} pages processed successfully")

    return results


# ---------------------------------------------------------------------------
# Single-PDF worker (the unit of work for the batch pool)
# ---------------------------------------------------------------------------

def _process_single_pdf(pdf_path, page_workers):
    """
    Process one PDF end-to-end.

    Returns (pdf_path, results_dict) on completion —
    individual page failures are captured inside results_dict,
    only truly fatal errors (corrupt PDF, missing file) raise.
    """
    try:
        results = process_pdf(pdf_path, max_workers=page_workers)
        return (pdf_path, results)
    except Exception as exc:
        logger.error(f"pdf failed: {pdf_path} — {exc}")
        return (pdf_path, {"total": 0, "ok": 0, "failed": [], "error": exc})


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def process_pdfs(pdf_paths, max_pdf_workers=2, max_page_workers=4):
    """
    Process multiple PDFs concurrently.

    Two levels of parallelism:
        max_pdf_workers  — how many PDFs run at the same time
        max_page_workers — threads per PDF for its pages

    Total peak threads ≈ max_pdf_workers × max_page_workers.
    Tune to your bottleneck:
        - API-bound (OCR, metadata)  → more page workers, fewer pdf workers
        - Lots of small PDFs         → more pdf workers, fewer page workers
        - Debugging                  → set both to 1

    Returns a list of (pdf_path, results_dict) in completion order.
    """
    all_results = []

    with ThreadPoolExecutor(max_workers=max_pdf_workers) as pool:
        future_to_pdf = {
            pool.submit(_process_single_pdf, path, max_page_workers): path
            for path in pdf_paths
        }

        for future in as_completed(future_to_pdf):
            pdf_path, results = future.result()
            all_results.append((pdf_path, results))

            error = results.get("error")
            if error:
                logger.error(f"[batch] {os.path.basename(pdf_path)}: fatal — {error}")
            elif results["failed"]:
                logger.warning(
                    f"[batch] {os.path.basename(pdf_path)}: "
                    f"{results['ok']}/{results['total']} ok, "
                    f"{len(results['failed'])} failed"
                )
            else:
                logger.info(
                    f"[batch] {os.path.basename(pdf_path)}: "
                    f"all {results['total']} pages ok"
                )

    # summary
    total_pdfs = len(pdf_paths)
    ok_pdfs = sum(1 for _, r in all_results if not r.get("error") and not r["failed"])
    logger.info(f"[batch] complete: {ok_pdfs}/{total_pdfs} PDFs fully successful")

    return all_results
def process_all_pdfs(directory):
    dirs,pdfs = get_files_and_dirs(directory,allowed_exts=['.pdf'])
    process_pdfs(pdfs, max_pdf_workers=2, max_page_workers=4)
