from .imports import *

# ── Schemas ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AnalysisRequest:
    """Payload sent to the analysis endpoint. Typos become loud AttributeErrors."""

    text: str
    scope: str = "full"
    summary_preset: str = "article"
    keyword_preset: str = "seo"

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "scope": self.scope,
            "summary_preset": self.summary_preset,
            "keyword_preset": self.keyword_preset,
        }


@dataclass(frozen=True)
class AnalysisConfig:
    """Explicit environment wiring — no hidden defaults."""

    endpoint: str = "https://clownworld.biz/hugpy/analyze/text"
    default_max_words: int = 510


# ── Helpers ──────────────────────────────────────────────────────────────────

def format_page_number(index: int) -> str:
    """Zero-based index → 1-based zero-padded string like '007'."""
    return f"{index + 1:03d}"


def format_page_key(index: int) -> str:
    return f"page_{format_page_number(index)}"


def truncate_to_word_limit(text: str, max_words: int = 5_000) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def page_index_from_path(path: str | Path) -> Optional[int]:
    """
    Extract the trailing integer from a filename like 'chapter_003.txt'.
    Returns None instead of silently coercing garbage to zero.
    """
    stem = os.path.dirname(str(path))
    suffix = stem.rsplit("_", maxsplit=1)[-1]
    if suffix.isdigit():
        return suffix
    return None


def print_page_info(analysis: dict, indent: int = 0) -> None:
    prefix = "  " * indent
    for key, value in analysis.items():
        print(f"{prefix}{key}")
        if isinstance(value, dict):
            print_page_info(value, indent + 1)
        else:
            print(f"{prefix}  {value}")


# ── Core analysis ────────────────────────────────────────────────────────────

def _build_request(
    text_path: str | Path,
    *,
    scope: Optional[str] = None,
    summary_preset: Optional[str] = None,
    keyword_preset: str = "seo",
    page_index: Optional[int] = None,
    max_words: int = 510,
) -> AnalysisRequest:
    """
    Read + truncate text, resolve scope/preset, return a validated request.
    Raises FileNotFoundError or ValueError — callers decide what to do.
    """
    path = Path(text_path)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")

    text = read_from_file(str(path))
    text = truncate_to_word_limit(text, max_words=max_words)

    if scope is None and page_index is not None:
        scope = f"page:{page_index}"
    elif scope is None and page_index is None and summary_preset == "brief":
        page_index = page_index_from_path(path)
        scope = f"page:{page_index}" if page_index is not None else "full"

    return AnalysisRequest(
        text=text,
        scope=scope or "full",
        summary_preset=summary_preset or "article",
        keyword_preset=keyword_preset,
    )


def analyze(
    text_path: str | Path,
    *,
    config: Optional[AnalysisConfig] = None,
    scope: Optional[str] = None,
    summary_preset: Optional[str] = None,
    keyword_preset: str = "seo",
    page_index: Optional[int] = None,
    max_words: Optional[int] = None,
) -> Optional[dict]:
    """
    Build a request and POST it. Returns the parsed response or None on failure.
    Exceptions propagate — the caller can log/retry/queue as they see fit.
    """
    config = config or AnalysisConfig()
    max_words = max_words or config.default_max_words

    request = _build_request(
        text_path,
        scope=scope,
        summary_preset=summary_preset,
        keyword_preset=keyword_preset,
        page_index=page_index,
        max_words=max_words,
    )
    return postRequest(config.endpoint, data=request.as_dict())


def analyze_page(
    text_path: str | Path,
    *,
    config: Optional[AnalysisConfig] = None,
    page_index: Optional[int] = None,
) -> Optional[dict]:
    if page_index is None:
        page_index = page_index_from_path(text_path)
    return analyze(
        text_path,
        config=config,
        summary_preset="brief",
        keyword_preset="seo",
        page_index=page_index,
        max_words=510,
    )


def analyze_full(
    text_path: str | Path,
    *,
    config: Optional[AnalysisConfig] = None,
) -> Optional[dict]:
    return analyze(
        text_path,
        config=config,
        scope="full",
        summary_preset="article",
        keyword_preset="seo",
        max_words=510,
    )


# ── Persistence ──────────────────────────────────────────────────────────────

def process_page_info(
    text_path: str | Path,
    *,
    config: Optional[AnalysisConfig] = None,
) -> Optional[Path]:
    """
    Analyze a page and merge the result into the sibling info.json.
    Returns the info_path on success, None on analysis failure.
    """
    result = analyze_page(text_path, config=config)
    if result is None:
        return None

    info_path = Path(text_path).parent / "info.json"

    if info_path.is_file():
        info = safe_load_from_json(str(info_path))
        info.update(result)
    else:
        info = result

    safe_dump_to_file(file_path=str(info_path), contents=info)
    logger.info("[process_page_info] wrote %s", info_path)
    return info_path
