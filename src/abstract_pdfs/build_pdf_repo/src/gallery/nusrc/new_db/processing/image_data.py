from .imports import *

# ── Schema ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OCRConfig:
    """Explicit wiring — swap the endpoint for tests or staging."""

    endpoint: str = "https://clownworld.biz/ocr/images/layout/to_text"
    fallback_text: str = "No Content"


# ── Core ─────────────────────────────────────────────────────────────────────

def image_to_text(
    image_path: str | Path,
    *,
    config: Optional[OCRConfig] = None,
) -> str:
    """
    POST an image path to the OCR endpoint and return the extracted text.
    Raises on network/server failure — caller decides retry/queue strategy.
    """
    config = config or OCRConfig()
    result = postRequest(config.endpoint, data={"image_path": str(image_path)})
    if not result:
        return config.fallback_text
    return result


def process_image(
    image_path: str | Path,
    *,
    config: Optional[OCRConfig] = None,
) -> Path:
    """
    OCR an image and write the result to a sibling text.txt.
    Returns the path to the written file.
    """
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"No such file: {image_path}")

    text = image_to_text(image_path, config=config)
    text_path = image_path.parent / "text.txt"

    safe_dump_to_file(file_path=str(text_path), contents=text)
    logger.info("[process_image] wrote %s", text_path)
    return text_path
