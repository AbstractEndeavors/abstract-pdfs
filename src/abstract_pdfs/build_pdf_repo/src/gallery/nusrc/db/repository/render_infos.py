import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from abstract_utilities import *
from pdf_renderer import *
from processing import process_page_info
from pathlib import Path
from datetime import datetime
import platform

PDF_DIRECTORY = "/srv/media/thedailydialectics/pdfs"
MAX_WORKERS = min(8, (os.cpu_count() or 4))


def info_in_with_txt_in_page_dir(txt_path):
    if os.path.isfile(txt_path):
        try:
            content = read_from_file(txt_path)
            file_parts = get_file_parts(txt_path)
            dirname = file_parts.get('dirname')
            info_path = os.path.join(dirname,'info.json')
            if os.path.isfile(info_path):
               return True 
        except Exception as e:
            print(f"{e}")
    return False
def get_txts_needing_info(pdf_directory: str) -> list[str]:
    """
    Find page image paths whose sibling text.txt does not exist.
    """
    dirs, all_txts = get_files_and_dirs(pdf_directory, allowed_exts=".txt")
    needs_infos = [txt_path for txt_path in all_txts if info_in_with_txt_in_page_dir(txt_path)]
    input(f"{len(needs_infos)} page infos needed")
    return list(reversed(needs_infos))


def safe_process_page_info(txt_path: str) -> tuple[str, bool, str | None]:
    """
    Wrap process_image so one failure does not kill the whole batch.
    """
    try:
        process_page_info(txt_path)
        return image_path, True, None
    except Exception as exc:
        return image_path, False, str(exc)


def main() -> None:
    needs_infos = get_txts_needing_info(PDF_DIRECTORY)

    if not needs_infos:
        print("No images require text extraction.")
        return

    print(f"Processing {len(needs_infos)} images with {MAX_WORKERS} threads...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(safe_process_page_info, txt_path): txt_path
            for txt_path in needs_infos
        }

        for future in as_completed(futures):
            info_path, success, error = future.result()
            if success:
                print(f"[OK] {info_path}")
            else:
                print(f"[FAIL] {info_path} :: {error}")


if __name__ == "__main__":
    main()


    
    
