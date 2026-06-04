"""
abstract_pdfs.enrichment.quality
================================
OCR-text and keyword quality heuristics.

This module exists because the upstream pipeline fed *raw* OCR straight into
keyword extraction and descriptions, so noise like ``teest``, ``b2%-``,
``nualeer.|`` and ``exp(x`` ended up as published SEO keywords.

Design goals:
  * **Pure standard library.**  No hard dependency on spaCy / KeyBERT / NLTK /
    wordfreq so it always runs, even in the local-fallback tier.
  * **Optional accuracy boosts.**  If ``wordfreq`` or a system word list is
    importable at runtime it is used to catch real misspellings the pure
    heuristic cannot (``teest`` -> not a word).  Never required.
  * **Deterministic & testable.**  Every function is a pure function of its
    inputs.

The two things callers want:
  * ``ocr_text_quality(text)`` -> 0..1 — how trustworthy is this OCR?  Drives
    the decision to fall back to a vision caption for the description.
  * ``clean_keywords(items)`` -> list — drop junk tokens / phrases before they
    become ``<meta name="keywords">``.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "token_quality",
    "phrase_quality",
    "is_wordlike",
    "clean_keywords",
    "ocr_text_quality",
    "split_sentences",
    "extractive_summary",
]

_VOWELS = set("aeiouy")
# A "word" for tokenisation: a run of letters, optionally with internal
# apostrophes/hyphens (e.g. "don't", "long-tail").
_WORD_RE = re.compile(r"[A-Za-z]+(?:['\-][A-Za-z]+)*")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Optional lexicon back-ends — lazy, guarded, cached.  Absence is fine.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _wordfreq_lookup():
    """Return a ``zipf_frequency`` callable, or None if wordfreq is absent."""
    try:
        from wordfreq import zipf_frequency  # type: ignore
        return zipf_frequency
    except Exception:
        return None


@lru_cache(maxsize=1)
def _system_words() -> Optional[frozenset]:
    """Load a system word list (``/usr/share/dict/words``) if present."""
    for path in ("/usr/share/dict/words", "/usr/share/dict/american-english"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                return frozenset(w.strip().lower() for w in fh if w.strip())
        except OSError:
            continue
    return None


def _in_lexicon(word: str) -> Optional[bool]:
    """Tri-state: True (known word), False (known non-word), None (unknown).

    Only returns a definite answer when a lexicon back-end is available.
    """
    w = word.lower().strip("'-")
    if not w:
        return None

    zipf = _wordfreq_lookup()
    if zipf is not None:
        # zipf scale: ~3+ is a common word, 0 means unseen.
        return zipf(w, "en") >= 2.0

    words = _system_words()
    if words is not None:
        return w in words

    return None


# ---------------------------------------------------------------------------
# Token / phrase scoring
# ---------------------------------------------------------------------------

def _max_consonant_run(core: str) -> int:
    run = best = 0
    for ch in core:
        if ch in _VOWELS:
            run = 0
        else:
            run += 1
            best = max(best, run)
    return best


def token_quality(token: str) -> float:
    """Score a single token's "word-likeness" in ``0.0 .. 1.0``.

    ``1.0`` — confidently a real/plausible word.
    ``0.0`` — junk (symbols, digits, no vowels, improbable letter runs).
    """
    if not token:
        return 0.0
    # Multi-line / tabbed fragments are OCR bleed, never a keyword.
    if "\n" in token or "\t" in token:
        return 0.0

    t = token.strip().lower()
    if not t:
        return 0.0

    # Strip the punctuation we tolerate *inside* words, then the core must be
    # pure ascii letters.  Anything else (digits, %, |, parens, dots) is junk.
    core = t.replace("-", "").replace("'", "").replace(" ", "")
    if not core or not core.isascii() or not core.isalpha():
        return 0.0

    # Definitive lexicon answer wins outright.
    known = _in_lexicon(t)
    if known is True:
        return 1.0
    if known is False:
        return 0.0

    n = len(core)
    if n < 2:
        return 0.1

    score = 1.0
    vowels = sum(c in _VOWELS for c in core)
    vr = vowels / n
    if vr == 0.0:                       # "kx", "gk", "lk" — no vowels
        return 0.0
    if vr < 0.18 or vr > 0.85:
        score -= 0.4

    run = _max_consonant_run(core)
    if run >= 5:
        score -= 0.6
    elif run >= 4:
        score -= 0.35

    if re.search(r"(.)\1\1", core):     # "eeee", triple repeats
        score -= 0.3

    if n == 2:
        score -= 0.35
    elif n == 3:
        score -= 0.1

    return max(0.0, min(1.0, score))


def phrase_quality(phrase: str) -> float:
    """Mean token quality over a phrase; a single junk word drags it down."""
    if not phrase:
        return 0.0
    if "\n" in phrase or "\t" in phrase:
        return 0.0
    words = _WORD_RE.findall(phrase)
    if not words:
        return 0.0
    scores = [token_quality(w) for w in words]
    mean = sum(scores) / len(scores)
    # A single clearly-junk word in an otherwise short phrase is damning.
    if min(scores) == 0.0 and len(words) <= 2:
        return min(mean, 0.25)
    return mean


def is_wordlike(token: str, threshold: float = 0.5) -> bool:
    return phrase_quality(token) >= threshold


# ---------------------------------------------------------------------------
# Keyword list cleaning
# ---------------------------------------------------------------------------

def _coerce_keyword(item) -> Optional[str]:
    """Normalise a keyword entry to a string.

    Accepts ``"word"`` or ``("phrase", 0.42)`` (KeyBERT style) or anything
    with a string-ish first element.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, (tuple, list)) and item:
        first = item[0]
        return first if isinstance(first, str) else None
    return None


def clean_keywords(
    items: Iterable,
    *,
    threshold: float = 0.5,
    max_keywords: Optional[int] = None,
    min_len: int = 2,
) -> List[str]:
    """Filter, normalise and de-duplicate a keyword list.

    Drops junk tokens (symbols/digits/improbable strings), collapses case and
    whitespace, and preserves first-seen order.
    """
    out: List[str] = []
    seen = set()
    for raw in items or []:
        kw = _coerce_keyword(raw)
        if not kw:
            continue
        kw = re.sub(r"\s+", " ", kw.strip())
        # Trim edge punctuation OCR loves to attach ("-abes", "value.").
        kw = kw.strip("-_.,|/\\()[]{}'\"·•:;!?")
        key = kw.lower()
        if not key or len(key) < min_len or key in seen:
            continue
        # A real keyword/phrase is letters + spaces + internal hyphen/apostrophe.
        # Embedded digits or symbols ("b2%-", "exp(x", "gk-2", "nualeer.|") are
        # the junk signal itself — reject the whole token, don't salvage it.
        if re.search(r"[^A-Za-z'\- ]", kw):
            continue
        if phrase_quality(kw) < threshold:
            continue
        seen.add(key)
        out.append(kw)
        if max_keywords and len(out) >= max_keywords:
            break
    return out


# ---------------------------------------------------------------------------
# Whole-text quality
# ---------------------------------------------------------------------------

def ocr_text_quality(text: str) -> float:
    """Estimate how clean an OCR text block is, in ``0.0 .. 1.0``.

    Roughly the fraction of word-like tokens, blended with their mean quality.
    Short blocks are treated cautiously (a 2-word block tells us little).
    """
    if not text or not text.strip():
        return 0.0
    words = _WORD_RE.findall(text)
    if not words:
        return 0.0
    scores = [token_quality(w) for w in words]
    n = len(scores)
    good = sum(1 for s in scores if s >= 0.5)
    frac_good = good / n
    mean = sum(scores) / n
    quality = 0.6 * frac_good + 0.4 * mean
    # Penalise the high-symbol-noise look of bad scans: lots of stray
    # non-alphanumeric characters relative to letters.
    letters = sum(c.isalpha() for c in text)
    symbols = sum((not c.isalnum()) and (not c.isspace()) for c in text)
    if letters:
        noise = symbols / letters
        if noise > 0.25:
            quality *= 0.7
        if noise > 0.5:
            quality *= 0.7
    return max(0.0, min(1.0, quality))


# ---------------------------------------------------------------------------
# Extractive summary (local-fallback summariser)
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> List[str]:
    if not text:
        return []
    flat = re.sub(r"\s+", " ", text.strip())
    return [s.strip() for s in _SENT_SPLIT_RE.split(flat) if s.strip()]


def extractive_summary(
    text: str,
    *,
    max_sentences: int = 3,
    max_words: int = 80,
    min_sentence_quality: float = 0.5,
) -> str:
    """A no-model summary: keep the cleanest, most substantial sentences.

    This is intentionally simple — it is the *fallback* when neither the
    in-process model nor the HTTP service is available.  Its job is to be
    honest (never invent text) and to avoid emitting OCR garbage.
    """
    sentences = split_sentences(text)
    if not sentences:
        return ""

    scored: List[Tuple[float, int, str]] = []
    for idx, sent in enumerate(sentences):
        words = _WORD_RE.findall(sent)
        if len(words) < 3:
            continue
        q = ocr_text_quality(sent)
        if q < min_sentence_quality:
            continue
        # Prefer cleaner, reasonably long, earlier sentences.
        length_bonus = min(len(words), 25) / 25.0
        position_bonus = 1.0 - (idx / max(len(sentences), 1)) * 0.3
        scored.append((q * 0.6 + length_bonus * 0.25 + position_bonus * 0.15, idx, sent))

    if not scored:
        # Nothing passed the gate — return the single best raw sentence so the
        # caller still gets *something* deterministic rather than empty.
        best = max(sentences, key=lambda s: ocr_text_quality(s))
        return _truncate_words(best, max_words)

    scored.sort(key=lambda t: t[0], reverse=True)
    chosen = sorted(scored[:max_sentences], key=lambda t: t[1])  # restore reading order
    summary = " ".join(s for _, _, s in chosen)
    return _truncate_words(summary, max_words)


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",;:") + "…"
