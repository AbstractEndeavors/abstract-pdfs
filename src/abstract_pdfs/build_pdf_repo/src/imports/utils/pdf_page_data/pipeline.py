from  .imports import *

def create_pdf_page_data(i, pdf_path, data):
    page_num_str = get_page_num_str(i)
    thumbnail_path = get_thumbnail(pdf_path, i)
    page_dir = os.path.dirname(thumbnail_path)
    json_path = os.path.join(page_dir, "info.json")
    html_path = os.path.join(page_dir, "index.html")

    # exists — read it
    if os.path.isfile(json_path) and os.path.isfile(html_path):
        logger.info("loaded page %d", i)
        return json.loads(Path(json_path).read_text())

    # doesn't exist — make it
    thumbnail_url = path_to_url(thumbnail_path)
    thumbnail_html_path = os.path.dirname(thumbnail_path)
    thumbnail_html_url = path_to_url(thumbnail_html_path)
    file_parts = get_file_parts(pdf_path)
    filename = file_parts.get("filename")
    pdf_title = filename.replace("_", "-")

    text_page_path = get_filtered_text_path(pdf_path, i)
    text_page_text = read_from_file(text_page_path)
    analyze_result = analyze_page(pdf_path, i)
    page_title = f"{pdf_title} | {page_num_str} | {thumbnail_html_url}"
    page_data = get_page_data(
        title=page_title,
        href=thumbnail_html_url,
        summary=analyze_result.get("summary", ""),
        keywords=analyze_result.get("keywords", {}).get("primary", []),
        thumbnail_url=thumbnail_url,
    )
    write_atomic(
        json_path,
        json.dumps(dict(page_data), indent=2, ensure_ascii=False),
    )
    html = build_image_html(
        page_data,
        href=thumbnail_html_url,
        thumbnail_url=thumbnail_url,
        text=text_page_text,
        path=thumbnail_html_path,
    )
    write_atomic(html_path, html)
    logger.info("wrote page %d → %s", i, page_dir)
    return page_data


def create_pdf_manifest_data(pdf_path, *, force=False):
    pdf_parts = get_file_parts(pdf_path)
    pdf_filename = pdf_parts.get('filename')
    pdf_dir = out_root = pdf_parts.get('dirname')
    manifest_path = os.path.join(out_root, "manifest.json")

    # already done — load and return
    if not force and os.path.isfile(manifest_path):
        existing = json.loads(Path(manifest_path).read_text())
        if existing.get("pages"):  # fully built, not just skeleton
            logger.info("skipping manifest — already done: %s", manifest_path)
            return existing

    pdf_href = path_to_url(pdf_dir)
    pdf_thumbnail_path = get_thumbnail(pdf_path, 1)
    pdf_thumbnail_url = path_to_url(pdf_thumbnail_path)
    pdf_title = pdf_filename.replace('_', '-')

    pdf_analyze_result = analyze_full(pdf_dir)
    pdf_keywords = pdf_analyze_result.get("keywords", {}).get("primary")
    pdf_meta_keywords = pdf_analyze_result.get("keywords", {}).get("meta")
    pdf_summary = pdf_analyze_result.get("summary")
    data = get_page_data(
        title=pdf_title,
        href=pdf_href,
        summary=pdf_summary,
        keywords=pdf_keywords,
        thumbnail_url=pdf_thumbnail_url,
    )
    data["title"] = pdf_title
    data["keywords"] = pdf_keywords
    data["thumbnail_url"] = pdf_thumbnail_url
    data["summary"] = pdf_summary
    reader = PyPDF2.PdfReader(pdf_path)
    page_count = len(reader.pages)
    data["page_count"] = page_count
    data["pages"] = []
    return data
# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# Content fetchers  (filesystem-backed, idempotent)
# ---------------------------------------------------------------------------

def assure_image(pdf_path, page_number):
    image_path = get_page_image_path_from_pdf_path(pdf_path, page_number)
    if not os.path.isfile(image_path):
        i = int(page_number)
        for _, image in pdf_to_images(pdf_path, first_page=i, last_page=i):
            image.save(image_path)
    return image_path

def check_text_content(content):
    if not content:
        return False
    if isinstance(content,dict) and content.get('error'):
        return False
    if content == "No Content":
        return False
    if "<Response " in content:
        return False
    return True
def check_text_path(text_path):
    if not text_path or not os.path.isfile(text_path):
        return False
    content = read_from_file(text_path)
    return check_text_content(content)
def get_plumber_text_content(pdf_path, page_number):
    return extract_single_pdf_page_text(pdf_path, int(page_number)-1)
def get_ocr_text_content(pdf_path, page_number):
    image_path = assure_image(pdf_path, page_number)
    if image_path and os.path.isfile(image_path):
        return postRequest(
                "https://ocr.abstractendeavors.com/images/layout/to_text",
                data={"image_path": image_path},
            )
def get_text_content(pdf_path, page_number):
    content = get_plumber_text_content(pdf_path, page_number)
    if not check_text_content(content):
        content = get_ocr_text_content(pdf_path, page_number)
    return content
def fetch_text_content(pdf_path, page_number):
    text_path = get_page_text_path_from_pdf_path(pdf_path, page_number)
    if check_text_path(text_path):
        content = read_from_file(text_path)
        if content:
            return content
    content = get_text_content(pdf_path, page_number)
    write_to_file(file_path=text_path, contents=content)
    return read_from_file(text_path)

TENANT_ID = "c16c16fd-e86e-4727-952c-dcb569c52f0d"
PDF_DIR = "/srv/media/thedailydialectics/pdfs"
POOL_SIZE = 8


# -----------------------------

def correct_meta_in_page_dir(pdf_path: str, page_dir: str, page_index: int) -> None:
    """
    Correct metadata for a single page directory.

    Args:
        pdf_path: Full path to the source PDF.
        page_dir: Full path to the page directory, e.g. /doc/pages/0001
        page_index: Zero-based page index for PDF extraction calls.
    """
    image_path = os.path.join(page_dir, "image.png")
    text_path = os.path.join(page_dir, "text.txt")
    info_path = os.path.join(page_dir, "info.json")
    metadata_path = os.path.join(page_dir, "metadata.json")

    if not os.path.isfile(info_path):
        return

    analyzed_data = safe_load_from_json(info_path)
    if not analyzed_data:
        return

    analyzed_data["image_path"] = image_path.replace(
        "/var/www/ABSTRACT_ENDEAVORS/media/TDD/srv/media/thedailydialectics",
        "/srv/media/thedailydialectics",
    )

    # If you actually want to persist extracted text, write it here.
    text_content = fetch_text_content(pdf_path, page_index)
    if text_content and not os.path.isfile(text_path):
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)

    safe_dump_to_json(file_path=info_path, data=analyzed_data)

    meta_info = get_meta_info(analyzed_data, page_dir, metadata_path)
    safe_dump_to_json(file_path=metadata_path, data=meta_info)


def correct_meta_data(pdf_file: str, max_workers: int = 8) -> None:
    """
    Correct metadata for all page directories in a PDF folder using threads.
    """
    pdf_dir = os.path.dirname(pdf_file)
    pages_dir = os.path.join(pdf_dir, "pages")

    if not os.path.isdir(pages_dir):
        return

    page_dirs = sorted(
        [
            os.path.join(pages_dir, item)
            for item in os.listdir(pages_dir)
            if os.path.isdir(os.path.join(pages_dir, item))
        ]
    )

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for page_index, page_dir in enumerate(page_dirs):
            futures.append(
                executor.submit(correct_meta_in_page_dir, pdf_file, page_dir, page_index)
            )

        for future in as_completed(futures):
            future.result()
