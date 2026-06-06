import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from abstract_utilities import *
from pdf_renderer import *
from processing import process_image
from pathlib import Path
from datetime import datetime
import platform

PDF_DIRECTORY = "/srv/media/thedailydialectics/pdfs"
MAX_WORKERS = min(8, (os.cpu_count() or 4))

def get_file_birth_time(path: str | Path) -> datetime | None:
    path = Path(path)

    result = subprocess.run(
        ["stat", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Birth:"):
            value = line.replace("Birth:", "", 1).strip()
            if value == "-" or not value:
                return None

            # Example: 2026-04-08 14:31:22.123456789 -0500
            main, _, tz = value.rpartition(" ")
            frac_split = main.split(".", 1)
            dt_base = frac_split[0]
        
            return datetime.strptime(f"{dt_base} {tz}", "%Y-%m-%d %H:%M:%S %z")

    return None
def is_no_context_in_time(file_path):
    time_cut = 1775671067.9195192
    if file_path and os.path.isfile(file_path):
        create_time = get_file_birth_time(file_path)
        ts_int = int(create_time.timestamp())
        if ts_int >time_cut:
            contents = read_from_file(file_path)
            if contents and 'No Content' in contents:
                return True
def text_in_dir(directory: str) -> bool:
    """
    Return True if the directory exists and does not yet contain text.txt.
    """
    if not os.path.isdir(directory):
        return False
    
    text_path = os.path.join(directory, "text.txt")
    return (not os.path.isfile(text_path) or is_no_context_in_time(text_path))


def get_images_needing_text(pdf_directory: str) -> list[str]:
    """
    Find page image paths whose sibling text.txt does not exist.
    """
    dirs, all_pngs = get_files_and_dirs(pdf_directory, allowed_exts=".png")
    print(f"{len(all_pngs)} images found")
    all_page_dirs = list({os.path.dirname(item) for item in all_pngs})
    print(f"{len(all_page_dirs)} page dirs found")
    page_texts = [os.path.join(item,'text.txt') for item in all_page_dirs]
    page_texts_needs_redo = [os.path.dirname(text) for text in page_texts if is_no_context_in_time(text)]
    print(f"{len(page_texts_needs_redo)} page texts need revsision")
    needs_texts= [os.path.dirname(text) for text in page_texts if not os.path.isfile(text)]
    print(f"{len(needs_texts)} page texts needed")
    all_page_texts = needs_texts+page_texts_needs_redo
    needs_texts = [os.path.join(item, "image.png") for item in all_page_texts]
##    needs_texts = [
##        os.path.join(item, "image.png")
##        for item in all_page_dirs
##        if text_in_dir(item)
##    ]
    print(f"{len(needs_texts)} page_images")
    return list(reversed(needs_texts))


def safe_process_image(image_path: str) -> tuple[str, bool, str | None]:
    """
    Wrap process_image so one failure does not kill the whole batch.
    """
    try:
        process_image(image_path)
        return image_path, True, None
    except Exception as exc:
        return image_path, False, str(exc)


def main() -> None:
    needs_texts = get_images_needing_text(PDF_DIRECTORY)

    if not needs_texts:
        print("No images require text extraction.")
        return

    print(f"Processing {len(needs_texts)} images with {MAX_WORKERS} threads...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(safe_process_image, image_path): image_path
            for image_path in needs_texts
        }

        for future in as_completed(futures):
            image_path, success, error = future.result()
            if success:
                print(f"[OK] {image_path}")
            else:
                print(f"[FAIL] {image_path} :: {error}")


if __name__ == "__main__":
    main()
def render_and_register(
    pdf_path,
    dpi: int = 200,
):
    
    pdf_dirname = os.path.dirname(pdf_path)
    try:
        pdf_path= Path(pdf_path)
        output_dir = Path(pdf_dirname)
        render_pdf_pages(
            pdf_path= pdf_path,
            output_dir=output_dir,
            dpi= 200,
            fmt= "png",
        )
    except:
        pass

##    for page in os.listdir(pages_dir):
##        page_image_path = os.path.join(pages_dir,page,'image.png')
##        page_text = image_to_text(
##            image_path=page_image_path
##            )
##        page_text_path = os.path.join(pages_dir,page,'text.txt')
##        write_to_file(file_path=page_text_path,contents=page_text)
##        analyzed_data = analyze_page(text_path = page_text_path)
##        page_info_path = os.path.join(pages_dir,page,'info.json')
##        safe_dump_to_json(file_path=page_info_path,data=analyzed_data)
##        analyzed_data['image_path']=page_image_path
##        meta_info = get_meta_info(analyzed_data)


    
    
