from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator


@dataclass(slots=True)
class ProcessResult:
    image_path: str
    success: bool
    error: str | None = None


def safe_process_image(
    image_path: str,
    processor: Callable[[str], None],
) -> ProcessResult:
    """
    Run the processor for a single image and trap exceptions so one
    failure does not stop the batch.
    """
    try:
        processor(image_path)
        return ProcessResult(image_path=image_path, success=True)
    except Exception as exc:
        return ProcessResult(
            image_path=image_path,
            success=False,
            error=str(exc),
        )


def process_images_serial(
    image_paths: Iterable[str],
    processor: Callable[[str], None],
) -> Iterator[ProcessResult]:
    """
    Process images one at a time, yielding results in input order.
    """
    for image_path in image_paths:
        yield safe_process_image(image_path=image_path, processor=processor)


def process_images_threaded(
    image_paths: Iterable[str],
    processor: Callable[[str], None],
    max_workers: int,
) -> Iterator[ProcessResult]:
    """
    Process images concurrently using threads, yielding results as they finish.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(safe_process_image, image_path, processor): image_path
            for image_path in image_paths
        }

        for future in as_completed(futures):
            yield future.result()


def process_images(
    image_paths: Iterable[str],
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
        yield from process_images_threaded(
            image_paths=image_paths,
            processor=processor,
            max_workers=max_workers,
        )
    else:
        yield from process_images_serial(
            image_paths=image_paths,
            processor=processor,
        )


def log_result(result: ProcessResult) -> None:
    """
    Standardized output for a processing result.
    """
    if result.success:
        print(f"[OK] {result.image_path}")
    else:
        print(f"[FAIL] {result.image_path} :: {result.error}")
