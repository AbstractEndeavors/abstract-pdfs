import os
from .page_nums import *
from .imports import *
def save_info(data,file_path):
    if data:
        safe_dump_to_json(data=data,file_path=file_path)
def write_atomic(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    write_to_file(file_path = tmp,contents=content)
    os.replace(tmp, path)

def getPath(path):
    if path and isinstance(path,str):
        path = Path(path)
    return path


def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()
def is_image(path):
    file_parts = get_file_parts(path)
    ext = file_parts.get('ext')
    if ext in IMAGE_EXTS:
        return True
    return False
    return name.replace("-", " ").replace("_", " ").title()
def is_image(path):
    file_parts = get_file_parts(path)
    ext = file_parts.get('ext')
    if ext in IMAGE_EXTS:
        return True
    return False
def get_pdf_dir(pdf_dir):
    if os.path.isfile(pdf_dir):
        pdf_dir = os.path.dirname(pdf_dir)
    return pdf_dir


def get_texts_dir(pdf_dir):
    pdf_dir = get_pdf_dir(pdf_dir)
    return os.path.join(pdf_dir,'text')

def get_thumbnails_dir(pdf_dir):
    pdf_dir = get_pdf_dir(pdf_dir)
    return os.path.join(pdf_dir,'thumbnails')

def get_thumbnail_dir(pdf_dir,i):
    thumbnails_dir = get_thumbnails_dir(pdf_dir)
    page_num_str = get_page_num_str(i)
    return os.path.join(thumbnails_dir,page_num_str)

def get_thumbnail(pdf_dir,i):
    thumbnail_dir = get_thumbnail_dir(pdf_dir,i)
    image_list = [os.path.join(thumbnail_dir,item) for item in os.listdir(thumbnail_dir) if is_image(item)]
    return image_list[0] if image_list else None


def _list_text_filenames(pdf_dir):
    return os.listdir(get_texts_dir(pdf_dir))


def is_valid_text_path(path, page_num_str=None):
    if not path:
        return False
    if page_num_str and path.endswith(f"{page_num_str}.txt"):
        return True
    if path.endswith("clean.txt"):
        return False
    return True


def get_filtered_text_paths(pdf_dir, page_num_str):
    texts_dir = get_texts_dir(pdf_dir)
    return [
        os.path.join(texts_dir, name)
        for name in _list_text_filenames(pdf_dir)
        if name.endswith(f"{page_num_str}.txt")
    ]

def get_filtered_text_path(pdf_dir, page_num_str):
    paths = get_filtered_text_paths(pdf_dir, page_num_str)
    return paths[0] if paths else ""

def get_filtered_text(pdf_dir, page_num_str):
    path = get_filtered_text_path(pdf_dir, page_num_str)
    return read_from_file(path) if path else ""


def get_unfiltered_text_paths(pdf_dir):
    texts_dir = get_texts_dir(pdf_dir)
    paths = [
        os.path.join(texts_dir, name)
        for name in _list_text_filenames(pdf_dir)
        if not name.endswith("clean.txt")
    ]
    paths.sort()
    return paths


def get_unfiltered_texts(pdf_dir):
    return [read_from_file(p) for p in get_unfiltered_text_paths(pdf_dir)]


def get_unfiltered_text(pdf_dir):
    return "\n".join(get_unfiltered_texts(pdf_dir))


def get_word_count_range(pdf_dir):
    texts = get_unfiltered_texts(pdf_dir)
    if not texts:
        return (0, 0)
    counts = [len(t.split()) for t in texts]
    return (min(counts), max(counts))
def truncate_to_word_limit(text, max_words=5_000):
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])
























