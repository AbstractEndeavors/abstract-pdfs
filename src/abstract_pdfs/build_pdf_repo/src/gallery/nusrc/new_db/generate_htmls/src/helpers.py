from .imports import *
# ═══════════════════════════════════════════════════════════════
# Text helpers
# ═══════════════════════════════════════════════════════════════


def clean_text(s: str | list, max_len: int = 160) -> str:
    if isinstance(s, list):
        s = str(s[0]) if s else ""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0] + "…"
    return s


def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


def breadcrumbs_html(base_url: str, site_root: str) -> str:
    path_part = base_url.rstrip("/").replace(site_root, "").lstrip("/")
    segments = [s for s in path_part.split("/") if s]
    crumbs = [f'<a href="{site_root}">Home</a>']
    acc = site_root
    for i, seg in enumerate(segments):
        acc += f"/{seg}"
        if i < len(segments) - 1:
            crumbs.append(f'<a href="{acc}/">{humanize(seg)}</a>')
        else:
            crumbs.append(f"<span>{seg}</span>")
    return " › ".join(crumbs)


def read_text_file(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def child_dirs(directory: Path) -> list[Path]:
    return sorted(
        d for d in directory.iterdir()
        if d.is_dir() and d.name not in SKIP_DIRS and not d.name.startswith(".")
    )


def first_image_url(directory: Path, resolver: PathResolver) -> str | None:
    for ext in IMAGE_EXTS:
        for hit in sorted(directory.rglob(f"*{ext}")):
            if hit.is_file():
                url = resolver.to_url(hit)
                if url:
                    return url
    return None


def load_manifest(directory: Path) -> list[dict] | None:
    """Load a manifest file from the directory (filesystem fallback)."""
    for name in [f"{directory.name}_manifest.json", "manifest.json"]:
        p = directory / name
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Bad manifest %s: %s", p, e)
    return None

