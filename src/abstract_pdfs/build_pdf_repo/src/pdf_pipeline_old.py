from .imports import *
from .generate_htmls import *
def safe_json_loads(obj):
    try:
        value = json.loads(str(obj))
        return value
    except Exception as e:
        logger.warning(f"{e}")
def image_needs_text(text_path):
    if not os.path.isfile(text_path):
        return True
    try:
        contents = read_from_file(text_path)
        print(contents)
        if not contents or contents.startswith("{'error':") or contents == 'No Content' or '<Response ' in contents:
            return True
        data = safe_json_loads(contents)
        print(data)
        if data and isinstance(data,dict) and data.get('error'):
            return True
    except Exception as e:
        logger.warning(f"{e}")
        return True
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
        pdf_dir = os.path.join(dirname,filename)
        os.makedirs(pdf_dir,exist_ok=True)
        nupdf_path = os.path.join(pdf_dir,basename)
        if not os.path.isfile(nupdf_path):
           shutil.move(pdf_path,nupdf_path) 
    else:
        pdf_dir = dirname
    return pdf_dir
def assure_pdf_path(pdf_path):
    pdf_dir = assure_pdf_dir(pdf_path)
    dir_parts = get_path_parts(pdf_dir)
    filename = dir_parts.get('filename')
    basename= f"{filename}.pdf"
    return os.path.join(pdf_dir,basename)
def assure_pages_dir_from_pdf_path(pdf_path):
    pdf_path = assure_pdf_path(pdf_path)
    pages_dir = get_pages_dir_from_pdf_path(pdf_path)
    os.makedirs(pages_dir,exist_ok=True)
    return pages_dir



def assure_page_dir_from_pdf_path(pdf_path, page_number):
    assure_pages_dir_from_pdf_path(pdf_path)
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    os.makedirs(page_dir,exist_ok=True)
    return page_dir

def assure_image(pdf_path, page_number):
    image_path = get_page_image_path_from_pdf_path(pdf_path, page_number)
    if not os.path.isfile(image_path):
        print(f"getting image for image_path {image_path}")
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
    image_path = assure_image(pdf_path, page_number)
    text= assure_text_from_pdf_path(pdf_path, page_number)
    info_path = get_page_info_path_from_pdf_path(pdf_path, page_number)
    if pdf_page_needs_info(info_path):
        print(f"getting info for info_path {info_path}")
        info = analyze_page(text=text,page_index=page_number)
        safe_dump_to_json(data=info.to_dict(),file_path=info_path)
        metadata_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
        if os.path.isfile(metadata_path):
            os.remove(metadata_path)
    return safe_load_from_json(info_path)    

def assure_metadata_from_pdf_path(pdf_path, page_number):
    assure_page_dir_from_pdf_path(pdf_path, page_number)
    image_path = assure_image(pdf_path, page_number)
    text= assure_text_from_pdf_path(pdf_path, page_number)
    info = assure_info_from_pdf_path(pdf_path, page_number)
    meta_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
    if pdf_page_needs_info(meta_path):
        metadata = get_metadata_info(pdf_path,page_number)
        safe_dump_to_json(file_path=meta_path, data=metadata)
    return safe_load_from_json(meta_path)
def assure_image_html(pdf_path, page_number):
    assure_metadata_from_pdf_path(pdf_path, page_number)
    image_path = assure_image(pdf_path, page_number)
    return get_image_page(image_path)
def process_pdf(pdf_path):
    pages_dir = assure_pages_dir_from_pdf_path(pdf_path)
    pdf_page_nums = get_num_pdf_pages(pdf_path=pdf_path)
    for i in range(pdf_page_nums):
        page_num_str = zero_it(i+1)
        assure_image_html(pdf_path, i+1)
    get_gallery_page(pages_dir)
    get_viewer_page(pdf_path)

