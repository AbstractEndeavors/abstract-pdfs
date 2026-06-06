from metadata import *
from abstract_utilities import *
from abstract_pdfs import extract_single_pdf_page_text, pdf_to_images
from multiprocessing import Pool

TENANT_ID = "c16c16fd-e86e-4727-952c-dcb569c52f0d"
PDF_DIR = "/srv/media/thedailydialectics/pdfs"
POOL_SIZE = 8


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def get_pages_dir_from_pdf_path(pdf_path):
    return os.path.join(get_file_parts(pdf_path).get('dirname'), 'pages')

def get_page_dir_from_pdf_path(pdf_path, page_number):
    return os.path.join(get_pages_dir_from_pdf_path(pdf_path), zero_buff_int(page_number, j=4))

def get_page_item_path_from_pdf_path(pdf_path, page_number, basename):
    return os.path.join(get_page_dir_from_pdf_path(pdf_path, page_number), basename)


# ---------------------------------------------------------------------------
# Content fetchers  (filesystem-backed, idempotent)
# ---------------------------------------------------------------------------

def assure_image(pdf_path, page_number):
    image_path = get_page_item_path_from_pdf_path(pdf_path, page_number, 'image.png')
    if not os.path.isfile(image_path):
        i = int(page_number)
        for _, image in pdf_to_images(pdf_path, first_page=i, last_page=i):
            image.save(image_path)
    return image_path


def fetch_text_content(pdf_path, page_number):
    text_path = get_page_item_path_from_pdf_path(pdf_path, page_number, 'text.txt')
    if os.path.isfile(text_path):
        content = read_from_file(text_path)
        if content:
            return content

    content = extract_single_pdf_page_text(pdf_path, page_number)
    if not content:
        image_path = get_page_item_path_from_pdf_path(pdf_path, page_number, 'image.png')
        content = postRequest(
            "https://ocr.abstractendeavors.com/images/layout/to_text",
            data={"image_path": image_path},
        )
    write_to_file(file_path=text_path, contents=content)
    return read_from_file(text_path)


def get_analysis(text_content, page_number):
    return postRequest(
        'https://hugpy.abstractendeavors.com/analyze/text',
        data={
            "text": text_content,
            "scope": f"page:{page_number}",
            "summary_preset": "brief",
            "keyword_preset": "seo",
            "input_policy": "allow",
        },
    )


def fetch_analysis(pdf_path, page_number):
    info_path = get_page_item_path_from_pdf_path(pdf_path, page_number, 'info.json')

    analysis = safe_load_from_json(info_path) if os.path.isfile(info_path) else None

    if not analysis or analysis.get('error'):
        text_content = fetch_text_content(pdf_path, page_number)

        if analysis and analysis.get('error'):
            # augment with path context before retrying
            p = get_file_parts(pdf_path)
            text_content = (
                f"{text_content} {p.get('basename')} page {page_number} "
                f"{p.get('parent_dirbase')} and {p.get('super_dirbase')} "
                f"from The Daily Dialectics thedailydialectics.com"
            )

        analysis = get_analysis(text_content, page_number)
        safe_dump_to_json(file_path=info_path, data=analysis)

    return safe_load_from_json(info_path)


def get_meta_info(analyzed_data, page_dir, metadata_path):
    image_path = analyzed_data.get("image_path")
    summary = analyzed_data.get("summary", "")
    keywords = analyzed_data.get("keywords", {})

    dirname = os.path.dirname(page_dir)
    dirbase = os.path.basename(dirname)
    parent_dirbase = os.path.basename(os.path.dirname(dirname))

    pdf_title = parent_dirbase.replace('_', '-').replace('--', '-')
    page_title = f"{pdf_title}-{dirbase}"
    alt = f"{pdf_title}-{dirbase} pdf Image"
    capt = summary[:67] if len(summary) > 67 else summary
    caption = f"{alt} {capt}..."
    href = path_to_url(image_path)

    meta_info = get_page_data(
        page_title, href, summary, keywords, thumbnail_url=href,
        alt=alt, caption=caption,
    )
    safe_dump_to_json(file_path=str(metadata_path), data=meta_info)
    return meta_info


def fetch_metadata(pdf_path, page_number):
    metadata_path = get_page_item_path_from_pdf_path(pdf_path, page_number, 'metadata.json')

    if os.path.isfile(metadata_path):
        meta_info = safe_load_from_json(metadata_path)
        if meta_info:
            return meta_info

    analysis = fetch_analysis(pdf_path, page_number)
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    meta_info = get_meta_info(analysis, page_dir, metadata_path)
    safe_dump_to_json(file_path=metadata_path, data=meta_info)
    return safe_load_from_json(metadata_path)


# ---------------------------------------------------------------------------
# Per-page processor  (owns its own connection — safe for multiprocessing)
# ---------------------------------------------------------------------------

def process_page(document_id: int, page_number: int, page_dir: str, pdf_path: str):
    conn = psycopg.connect(conninfo=DATABASE_URL, autocommit=True)
    try:
        repo = Repository(conn)

        page = repo.upsert_page(
            document_id=document_id,
            page_number=page_number,
            image_path=os.path.join(page_dir, "image.png"),
            text_path=os.path.join(page_dir, "text.txt"),
            info_path=os.path.join(page_dir, "info.json"),
            metadata_path=os.path.join(page_dir, "metadata.json"),
        )

        assure_image(pdf_path, page_number)
        text_content = fetch_text_content(pdf_path, page_number)
        analysis = fetch_analysis(pdf_path, page_number)
        metadata = fetch_metadata(pdf_path, page_number)

        repo.save_page_content(
            page_id=page.id,
            text_content=text_content,
            analysis=analysis,
            metadata=metadata,
        )
        repo.mark_page_complete(page.id)
        print(f"  page {page_number} done")

    except Exception as e:
        print(f"  page {page_number} failed: {e}")
    finally:
        conn.close()


def process_page_wrapper(args):
    doc_id, page_number, page_dir, pdf_path = args
    process_page(doc_id, page_number, page_dir, pdf_path)


# ---------------------------------------------------------------------------
# Document registration
# ---------------------------------------------------------------------------

def get_doc_from_pdf_path(repo, pdf_path):
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return None

    parts = get_file_parts(pdf_path)
    dirname = parts.get('dirname')
    slug = parts.get('dirbase')

    try:
        reader = PyPDF2.PdfReader(pdf_path)
        page_count = len(reader.pages)
    except Exception as e:
        print(f"Could not read {pdf_path}: {e}")
        return None

    doc = repo.get_document_by_hash(TENANT_ID, identity_hash(slug))
    if doc is None:
        doc = repo.insert_document(
            tenant_id=TENANT_ID,
            slug=slug,
            base_path=dirname,
            pdf_path=pdf_path,
            discriminator="",
        )
        doc = repo.update_page_count(doc.id, page_count)
        print(f"Created document: {slug}")
    else:
        print(f"Document exists: {slug}")

    return doc
def ensure_pages_dir(doc):
    pages_dir = os.path.join(doc.base_path, 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    return pages_dir
def get_page_jobs(doc):
    print(f"Processing {doc.slug}...")
    pages_dir = ensure_pages_dir(doc)
    repo.ensure_document_pages(doc.id, doc.page_count)
    page_jobs = []
    for i in range(1, doc.page_count + 1):
        page_dir = os.path.join(pages_dir, f"{i:04d}")
        os.makedirs(page_dir, exist_ok=True)
        page_jobs.append((doc.id, i, page_dir, pdf_path))

    with Pool(processes=POOL_SIZE) as pool:
        pool.map(process_page_wrapper, page_jobs)

    repo.update_document_status(doc.id, Status.COMPLETE)
