from .imports import *


def get_type_exts(typ):
    return list(MIME_TYPES.get(typ,{}).keys())
def get_img_exts():
    return get_type_exts('image')
def get_video_exts():
    return get_type_exts('video')

def find_files_by_ext(root, exts, recursive=True):
    """Walk root and yield files matching any extension in exts."""
    if not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # sort for determinism
        for fname in sorted(filenames):
            if os.path.splitext(fname)[1].lower() in exts:
                yield os.path.join(dirpath, fname)
        if not recursive:
            break

def first_existing_file(*paths):
    """Return the first path that exists as a file, or ''."""
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return ""

def child_dirs(directory, skip_dirs):
    """List immediate child directories, excluding skip set and dotfiles."""
    if not os.path.isdir(directory):
        return []
    result = []
    for name in sorted(os.listdir(directory)):
        full = os.path.join(directory, name)
        if os.path.isdir(full) and name not in skip_dirs and not name.startswith("."):
            result.append(full)
    return result
def get_dirbase(directory):
    dirname = os.path.dirname(directory)
    return os.path.basename(dirname)
def get_parent_dirbase(directory):
    dirname = os.path.dirname(directory)
    dirbase = os.path.basename(dirname)
    parent_dirname = os.path.dirname(dirname)
    return os.path.basename(parent_dirname)
def get_pages_dir_from_pdf_path(pdf_path):
    return os.path.join(get_file_parts(pdf_path).get('dirname'), 'pages')
def get_page_dir_from_pdf_path(pdf_path, page_number):
    return os.path.join(get_pages_dir_from_pdf_path(pdf_path), zero_buff_int(page_number, j=4))
def get_page_item_path_from_pdf_path(pdf_path, page_number, basename):
    return os.path.join(get_page_dir_from_pdf_path(pdf_path, page_number), basename)
def get_page_image_path_from_pdf_path(pdf_path, page_number):
    return get_page_item_path_from_pdf_path(pdf_path, page_number, 'image.png')
def get_page_text_path_from_pdf_path(pdf_path, page_number):
    return get_page_item_path_from_pdf_path(pdf_path, page_number, 'text.txt')
def get_page_info_path_from_pdf_path(pdf_path, page_number):
    return get_page_item_path_from_pdf_path(pdf_path, page_number, 'info.json')
def get_page_meta_path_from_pdf_path(pdf_path, page_number):
    return get_page_item_path_from_pdf_path(pdf_path, page_number, 'metadata.json')
def get_pdf_title_from_pdf_path(pdf_path, page_number):
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    parent_dirbase = get_parent_dirbase(page_dir)
    return parent_dirbase.replace('_','-').replace('_','-').replace('--','-')
def get_page_title_from_pdf_path(pdf_path, page_number):
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    dirbase = get_dirbase(page_dir)
    pdf_title = get_pdf_title_from_pdf_path(pdf_path, page_number)
    return f"{pdf_title}-{dirbase}"
def get_page_alt_from_pdf_path(pdf_path, page_number):
    page_title = get_page_title_from_pdf_path(pdf_path, page_number)
    return f"{page_title} pdf Image"    
def get_info_from_pdf_path(pdf_path, page_number):
    info_path  = get_page_info_path_from_pdf_path(pdf_path, page_number)
    return safe_load_from_json(info_path)
def get_info_keywords_from_pdf_path(pdf_path, page_number):
    info = get_info_from_pdf_path(pdf_path, page_number)
    return info.get("keywords", "")
def get_info_summary_from_pdf_path(pdf_path, page_number):
    info = get_info_from_pdf_path(pdf_path, page_number)
    return info.get("summary", "")
def get_caption_from_pdf_path(pdf_path, page_number):
    alt = get_page_alt_from_pdf_path(pdf_path, page_number)
    summary = get_info_summary_from_pdf_path(pdf_path, page_number)
    capt = summary[:67] if len(summary) >67 else summary
    return f"{alt} {capt}..."     
