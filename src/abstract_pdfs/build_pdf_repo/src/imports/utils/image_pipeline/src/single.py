from __future__ import annotations

from typing import Callable

from .runner import ProcessResult, log_result, safe_process_image


def process_one_image(
    image_path: str,
    processor: Callable[[str], None],
    *,
    log: bool = True,
) -> ProcessResult:
    """
    Direct single-image execution with the same safety wrapper used by batch mode.
    """
    result = safe_process_image(image_path=image_path, processor=processor)
    if log:
        log_result(result)
    return result
