from __future__ import annotations

from .runner import log_result, process_images,safe_process_image
from .imports import *
MAX_WORKERS = 8
def safe_json_loads(obj):
    try:
        return json.loads(str(obj))
    except Exception as e:
        logger.warning(f"{e}")
        return None


def image_needs_text(text_path):
    if not os.path.isfile(text_path):
        return True
    try:
        contents = read_from_file(text_path)
        if not contents or contents.startswith("{'error':") or contents == 'No Content' or '<Response ' in contents:
            return True
        data = safe_json_loads(contents)
        if data and isinstance(data, dict) and data.get('error'):
            return True
    except Exception as e:
        logger.warning(f"{e}")
        return True
    return False
def get_images_needing_text(pdf_directory: str) -> list[str]:
    """
    Find page image paths whose sibling text.txt does not exist.
    """
    dirs, all_pngs = get_files_and_dirs(pdf_directory, allowed_exts=".png")

    all_page_dirs = list({os.path.dirname(item) for item in all_pngs})

    page_texts = [os.path.join(item,'text.txt') for item in all_page_dirs]
    needs_texts= [os.path.dirname(text) for text in page_texts if image_needs_text(text_path)]

    all_page_texts = needs_texts
    needs_texts = [os.path.join(item, "image.png") for item in all_page_texts]

    return list(reversed(needs_texts))


def get_needed_texts(
    *,
    threaded: bool = True,
    max_workers: int = MAX_WORKERS,
) -> None:
    needs_texts = get_images_needing_text(TDD_PDFS_DIR)

    if not needs_texts:
        print("No images require text extraction.")
        return

    mode = "threaded" if threaded else "single-threaded"
    print(
        f"Processing {len(needs_texts)} images in {mode} mode "
        f"(max_workers={max_workers})..."
    )

    for result in process_images(
        needs_texts,
        safe_process_image,
        threaded=threaded,
        max_workers=max_workers,
    ):
        log_result(result)
