from .imports import *
# ─────────────────────────────────────────────────────────────────────────────
# Probers — extract real data from files
# ─────────────────────────────────────────────────────────────────────────────

def probe_image(path: Path) -> tuple[int, int, float]:
    """Return (width, height, file_size_mb). Falls back to (0, 0, size) if no PIL."""
    path = get_pathlib_path(path)
    size_mb = round(path.stat().st_size / 1_048_576, 3)
    if not HAS_PIL:
        return 0, 0, size_mb
    try:
        with PILImage.open(path) as img:
            w, h = img.size
        return w, h, size_mb
    except Exception:
        return 0, 0, size_mb


def slug_from_path(path: str) -> str:
    """Convert a filename to a URL-friendly slug."""
    name = get_safe_filename(path)
    name = re.sub(r'[^a-zA-Z0-9\-_]', '-', name)
    name = re.sub(r'-+', '-', name).strip('-').lower()
    return name


def keywords_from_text(text: str, max_words: int = 12) -> str:
    """Extract likely keywords from text (frequency + OCR-quality gate).

    Filters OCR junk (symbols/digits/improbable strings) so noise like
    ``b2%-`` or ``nualeer.|`` never becomes a published keyword.
    """
    stopwords = {
        'the','a','an','and','or','of','in','on','to','for','with','is','are',
        'was','were','that','this','it','at','by','from','as','be','has','had',
        'its','not','but','can','we','he','she','they','their','our','1','2',
        '3','4','5','6','7','8','9','0',
    }
    try:
        from abstract_pdfs.enrichment.quality import token_quality
    except Exception:
        token_quality = None

    words = re.findall(r"[a-zA-Z]{3,}", text)
    freq: dict[str, int] = {}
    for w in words:
        lower = w.lower()
        if lower in stopwords:
            continue
        if token_quality is not None and token_quality(lower) < 0.6:
            continue
        freq[lower] = freq.get(lower, 0) + 1
    top = sorted(freq, key=lambda k: freq[k], reverse=True)[:max_words]
    return ",".join(w.capitalize() for w in top)

