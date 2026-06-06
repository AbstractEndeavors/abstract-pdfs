from .imports import *
def join_pathlike(path,rel):
    path = eatOuter(path,'/')
    rel = eatInner(rel,'/')
    return f"{path}/{rel}"
##def path_to_url(path):
##    rel_path = str(path).replace(MEDIA_ROOT,"")
##    return join_pathlike(ROOT_URL,rel_path)
##def url_to_path(url):
##    rel_path = url.replace(ROOT_URL,"")
##    return join_pathlike(MEDIA_ROOT,rel_path)
def path_to_url_info(path):
    dirname = os.path.dirname(path)       
    return path_to_url(dirname)
def convert_paths_to_urls(data,base_url=None):
    base_url = base_url or ROOT_URL
    return join_pathlike(MEDIA_ROOT,base_url)
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

def path_to_url(path, media_root=None, site_root=None):
    """Convert an absolute filesystem path to a public URL."""

    if not path:
        return ""
    site_root = site_root or TDD_ROOT_URL
    media_root = media_root or TDD_MEDIA_ROOT_DIR
    real = os.path.realpath(str(path))
    root_real = os.path.realpath(str(media_root))
    if not real.startswith(root_real):
        return ""
    rel = real[len(root_real):].lstrip(os.sep)
    return "%s/%s" % (site_root.rstrip("/"), rel.replace(os.sep, "/")) if rel else site_root.rstrip("/") + "/"


def url_to_path(url, media_root=None, site_root=None):
    """Convert a public URL back to a filesystem path, or None."""
    site_root = site_root or TDD_ROOT_URL
    media_root = media_root or TDD_MEDIA_ROOT_DIR
    if not url or site_root not in url:
        return None
    rel = url.replace(site_root, "").lstrip("/")
    candidate = os.path.join(media_root, rel)
    return candidate if os.path.exists(candidate) else None
