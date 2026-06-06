from .imports import *
from .info_pipeline import *
from .image_pipeline import *
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
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    os.makedirs(page_dir,exist_ok=True)


def assure_image(pdf_path, page_number):
    image_path = get_page_image_path_from_pdf_path(pdf_path, page_number, 'image.png')
    if not os.path.isfile(image_path):
        i = int(page_number)
        for _, image in pdf_to_images(pdf_path, first_page=i, last_page=i):
            image.save(image_path)
    return image_path

def assure_text_from_pdf_path(pdf_path, page_number):
    image_path = assure_image(pdf_path, page_number)
    text_path = process_image(image_path)
    return read_from_file(text_path)
    
def assure_info_from_pdf_path(pdf_path, page_number):
    image_path = assure_image(pdf_path, page_number)
    text= assure_text_from_pdf_path(pdf_path, page_number)
    info_path = get_page_info_path_from_pdf_path(pdf_path, page_number)
    if pdf_page_needs_info(info_path):
        info = analyze_page(text=text)
        input(info)
        safe_dump_to_json(data=info.to_dict(),file_path=info_path)
    return safe_load_from_json(info_path)    

def assure_metadata_from_pdf_path(pdf_path, page_number):
    image_path = assure_image(pdf_path, page_number)
    text= assure_text_from_pdf_path(pdf_path, page_number)
    info = assure_info_from_pdf_path(pdf_path, page_number)
    meta_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
    if pdf_page_needs_info(meta_path):
        metadata = get_metadata_info(pdf_path,page_number)
        safe_dump_to_json(file_path=meta_path, data=metadata.to_dict())
    return safe_load_from_json(meta_path)
def process_pdf(pdf_path):
    pages_dir = assure_pages_dir_from_pdf_path(pdf_path)
    pdf_page_nums = get_num_pdf_pages(pdf_path=pdf_path)
    for i in range(pdf_page_nums):
        page_num_str = zero_it(i+1)
        assure_metadata_from_pdf_path(pdf_path, page_num_str)

