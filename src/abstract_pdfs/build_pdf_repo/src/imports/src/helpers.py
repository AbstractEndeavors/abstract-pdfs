from .init_imports import *
from .urls import *
from .constants import *
def humanize(name: str) -> str:
    if not name:
        return name.replace("-", " ").replace("_", " ").title()
    return name

def clean_text(s: str, max_len: int = 160) -> str:
    """Collapse whitespace and trim to max_len."""
    if isinstance(s,list):
        s = str(','.join(s))
        
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(' ', 1)[0] + '…'
    return s


def child_dirs(directory: Path) -> list[Path]:
    return sorted(
        d for d in directory.iterdir()
        if d.is_dir() and d.name not in SKIP_DIRS and not d.name.startswith(".")
    )


def load_manifest(directory: Path) -> Optional[list[dict]]:
    for name in [f"{directory.name}_manifest.json", "manifest.json"]:
        p = directory / name
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError) as e:
            print(f"[warn] bad manifest {p}: {e}")
    return None


def first_real_image_url(directory: Path, media_root: Path, site_root: str) -> Optional[str]:
    for ext in IMAGE_EXTS:
        for hit in sorted(directory.rglob(f"*{ext}")):
            if hit.is_file():
                try:
                    return path_to_url(hit, media_root, site_root)
                except ValueError:
                    continue
    return None


def breadcrumbs(base_url: str) -> str:
    path_part = base_url.rstrip("/").replace(SITE_ROOT, "").lstrip("/")
    segments  = [s for s in path_part.split("/") if s]
    crumbs    = [f'<a href="{SITE_ROOT}">Home</a>']
    acc       = SITE_ROOT
    for i, seg in enumerate(segments):
        acc += f"/{seg}"
        if i < len(segments) - 1:
            crumbs.append(f'<a href="{acc}/">{humanize(seg)}</a>')
        else:
            crumbs.append(f"<span>{seg}</span>")
    return " › ".join(crumbs)


def extract_description(manifest: list[dict]) -> str:
    """
    Pull the best available description from a manifest.
    Priority: longdesc (OCR text) → caption → keywords_str
    Cleans whitespace and truncates to ~160 chars.
    """
    first = manifest[0]
    raw = (
        first.get("longdesc")
        or first.get("caption")
        or first.get("keywords_str", "").replace(",", " ")
        or ""
    )
    return clean_text(raw, 160)


def extract_keywords(manifest: list[dict], limit: int = 8) -> list[str]:
    """Aggregate keywords across all pages, deduplicated, capped at limit."""
    seen:  set[str] = set()
    out:   list[str] = []
    for entry in manifest:
        for kw in entry.get("keywords_str", "").split(","):
            kw = kw.strip()
            kl = kw.lower()
            if kw and kl not in seen and len(kl) > 2:
                seen.add(kl)
                out.append(kw)
                if len(out) >= limit:
                    return out
    return out
