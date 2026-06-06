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
