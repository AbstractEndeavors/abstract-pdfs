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


def _apply_quality_gate(response, text, *, image_path=None, describe="__unset__"):
    """Clean OCR-junk keywords in place and optionally swap in a vision caption.

    Schema-preserving: mutates ``response.keywords`` (a RefinedResult) and,
    when warranted, ``response.summary`` — so ``response.to_dict()`` keeps the
    exact same keys, just cleaner values. Never raises; the pipeline must
    survive even if the enrichment layer is unavailable.
    """
    try:
        import re as _re
        from abstract_pdfs.enrichment import quality
        from abstract_pdfs.enrichment.config import EnrichmentConfig
    except Exception as exc:  # enrichment unavailable — leave response untouched
        logger.info(f"quality gate skipped (enrichment unavailable): {exc}")
        return response

    kw = getattr(response, "keywords", None)
    if kw is not None:
        before = list(getattr(kw, "primary", []) or []) + list(getattr(kw, "secondary", []) or [])
        primary = quality.clean_keywords(getattr(kw, "primary", []) or [], threshold=0.5, max_keywords=15)
        secondary = quality.clean_keywords(getattr(kw, "secondary", []) or [], threshold=0.5)
        seen = {k.lower() for k in primary}
        secondary = [k for k in secondary if k.lower() not in seen]
        kept = {k.lower() for k in primary + secondary}
        dropped = [k for k in before if isinstance(k, str) and k.lower() not in kept]

        kw.primary = primary
        kw.secondary = secondary
        kw.dropped = sorted(set(list(getattr(kw, "dropped", []) or []) + dropped))
        meta_list = primary[:15]
        kw.meta_keywords = ", ".join(meta_list)
        kw.hashtags = ["#" + _re.sub(r"[^a-z0-9]+", "", k.lower()) for k in meta_list]
        kw.slug_candidates = [s for s in (_re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-") for k in primary[:5]) if s]

    # Optional vision description for poor-OCR pages (configurable via env/param).
    try:
        cfg = (EnrichmentConfig.resolve(None, describe=describe)
               if describe != "__unset__" else EnrichmentConfig.from_env())
        dcfg = cfg.describe
        if dcfg and image_path and dcfg.wants_vision(quality.ocr_text_quality(text)):
            from abstract_pdfs.enrichment.providers import vision_caption
            caption = vision_caption(image_path, dcfg)
            if caption:
                response.summary = caption
    except Exception as exc:
        logger.info(f"vision description skipped: {exc}")

    return response


def analyze_page(text_path=None, text=None, page_index=None, image_path=None, describe="__unset__"):
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
        # Clean OCR-junk keywords + optional vision description (no-op if the
        # enrichment layer or models are unavailable).
        response = _apply_quality_gate(response, text, image_path=image_path, describe=describe)
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
