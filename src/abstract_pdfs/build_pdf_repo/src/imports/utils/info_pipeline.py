from __future__ import annotations

from abstract_hugpy import analyze_media_text,refine_keywords,PDFSeoResult,summarize
from .imports import *
from .utils import *

def _analyze(
    text: str,
    scope: str,
    *,
    summary_preset: str = "article",
    keyword_preset: str = "seo",
    input_policy:str="allow"
) -> PDFSeoResult:
    """Run summary + keywords on a single block of text."""
    result = PDFSeoResult(scope=scope, text=text)
    result.summary = summarize(text, preset=summary_preset)
    result.keywords = refine_keywords(text, preset=keyword_preset)
    return result

@dataclass(slots=True)
class ProcessInfoResult:
    image_path: str
    success: bool
    error: str | None = None
MAX_WORKERS = 8
def analyze_page(text_path=None,text=None,page_index=None):
    if text_path and not text:
        file_parts = get_file_parts(text_path)
        page_index = file_parts.get('dirbase')
        text = read_from_file(text_path)
    if text:
        text = truncate_to_word_limit(text, max_words=510)
        data={"text":text,
        "scope":f"page:{page_index}",
        "summary_preset":"brief",         # one page ≠ article-length
        "keyword_preset":"seo"}
        logger.info(f"analyze_page data = {data}")
        response = analyze_media_text(**data)#postRequest('https://hugpy.abstractendeavors.com/analyze/text',data=data)
        logger.info(f"response = {response}")
        return response

def safe_process_info(
    text_path: str,
    processor: Callable[[str], None],
) -> ProcessResult:
    """
    Run the processor for a single image and trap exceptions so one
    failure does not stop the batch.
    """
    try:
        info = processor(text_path)
        safe_dump_to_json(data=info,file_path=text_path.replace('text.txt','info.json'))
        return ProcessInfoResult(text_path=text_path, success=True)
    except Exception as exc:
        return ProcessResult(
            text_path=text_path,
            success=False,
            error=str(exc),
        )


def process_infos_threaded(
    text_paths: Iterable[str],
    processor: Callable[[str], None],
    max_workers: int,
) -> Iterator[ProcessResult]:
    """
    Process images concurrently using threads, yielding results as they finish.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(safe_process_info, text_path, processor): text_path
            for text_path in text_paths
        }
        
        for future in as_completed(futures):
            yield future.result()
def process_infos_serial(
    text_paths: Iterable[str],
    processor: Callable[[str], None],
) -> Iterator[ProcessResult]:
    """
    Process images one at a time, yielding results in input order.
    """
    for text_path in text_paths:
        yield safe_process_info(text_path=text_path, processor=processor)



def process_infos(
    text_paths: Iterable[str],
    processor: Callable[[str], None],
    *,
    threaded: bool = True,
    max_workers: int = 4,
) -> Iterator[ProcessResult]:
    """
    Unified runner.

    Set threaded=False to force single-threaded execution while keeping
    the same external interface.
    """
    if threaded:
        yield from process_infos_threaded(
            text_paths=text_paths,
            processor=processor,
            max_workers=max_workers,
        )
    else:
        yield from process_infos_serial(
            text_paths=text_paths,
            processor=processor,
        )

def pdf_page_needs_info(info_path):
    if not os.path.isfile(info_path):
        return True
    try:
        data =safe_load_from_json(info_path) or {}
        if not data or not isinstance(data,dict) or data.get('error') or '<Response ' in data:
            return True
    except:
        return True
def get_texts_needing_info(pdf_directory: str) -> list[str]:
    """
    Find page image paths whose sibling text.txt does not exist.
    """
    dirs, all_txts = get_files_and_dirs(pdf_directory, allowed_exts=".txt")

    all_page_dirs = list({os.path.dirname(item) for item in all_txts})

    page_infos = [os.path.join(item,'info.json') for item in all_page_dirs]
    info_needs_infos= [path for path in page_infos if pdf_page_needs_info(path)]
    needs_infos= [path.replace('info.json','text.txt') for path in info_needs_infos ]
    return list(reversed(needs_infos))


def get_needed_infos(
    *,
    threaded: bool = True,
    max_workers: int = MAX_WORKERS,
) -> None:
    text_paths = get_texts_needing_info(TDD_PDFS_DIR)
    for path in text_paths:
        input(analyze_page(path))
    if not text_paths:
        print("No texts require info extraction.")
        return

    mode = "threaded" if threaded else "single-threaded"
    print(
        f"Processing {len(text_paths)} images in {mode} mode "
        f"(max_workers={max_workers})..."
    )

    for result in process_infos(
        text_paths,
        analyze_page,
        threaded=threaded,
        max_workers=max_workers,
    ):
        log_result(result) 
