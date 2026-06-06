from .init_imports import *
from .constants import TDD_ROOT_URL,TDD_MEDIA_ROOT_DIR,TDD_ROOT_DIR
from .utils import getPath
def url_to_path(
    url: str,
    media_root: Path or str=None,
    site_root: str=None
    ) -> Optional[Path]:
    site_root = site_root or TDD_ROOT_URL
    if not url or site_root not in url:
        return None
    media_root = media_root or TDD_MEDIA_ROOT_DIR
    rel = url.replace(site_root, "").lstrip("/")
    return getPath(media_root) / rel
def get_rel(string,root):
    if root and root in string:
        return string.replace(root, "").lstrip("/")

def get_rel_path_to_media(path):

    return get_rel(path,TDD_MEDIA_ROOT_DIR)
def get_rel_path_to_root(path):
    return get_rel(path,TDD_ROOT_DIR)
def get_rel_tdd_path(path,root = None):
    rel_path = None
    if not root:
        rel_path = get_rel(path,root)
    if not rel_path:
        rel_path = get_rel_path_to_media(path)
    if not rel_path:
        rel_path = get_rel_path_to_root(path)
    return rel_path
def path_to_url(
    path: Path,
    path_root: str or Path = None,
    site_root: str=None
    ) -> str:
    site_root = site_root or TDD_ROOT_URL
    rel_path = get_rel_tdd_path(path,path_root)
    if rel_path:
        return f"{site_root}/{rel_path}"


def find_correct_path(
    broken: Path,
    media_root: Path
    ) -> Optional[Path]:
    target = broken.name
    if not target:
        return None
    matches = list(media_root.rglob(target))
    if len(matches) == 1:
        return matches[0]
    parent_name = broken.parent.name
    for m in matches:
        if m.parent.name == parent_name:
            return m
    return None


def verified_url(
    url: str,
    media_root: Path,
    site_root: str
    ) -> Optional[str]:
    if not url:
        return None
    expected = url_to_path(url, media_root, site_root)
    if expected is None:
        return url
    if expected.exists():
        return url
    correct = find_correct_path(expected, media_root)
    return path_to_url(correct, media_root, site_root) if correct else None

