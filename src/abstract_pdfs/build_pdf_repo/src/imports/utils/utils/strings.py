from .imports import *
def clean_text(s: str, max_len: int = 200) -> str:
    if isinstance(s,list):
        s = str(s[0])
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(' ', 1)[0] + '…'
    return s



def breadcrumbs_html(url, site_root):
    """Generate breadcrumb HTML from a URL."""
    path_part = url.rstrip("/").replace(site_root, "").lstrip("/")
    segments = [s for s in path_part.split("/") if s]
    crumbs = ['<a href="%s">Home</a>' % site_root]
    acc = site_root
    for i, seg in enumerate(segments):
        acc += "/%s" % seg
        if i < len(segments) - 1:
            crumbs.append('<a href="%s/">%s</a>' % (acc, humanize(seg)))
        else:
            crumbs.append("<span>%s</span>" % seg)
    return " › ".join(crumbs)

def humanize(name):
    """'some_slug-name' -> 'Some Slug Name'"""
    return name.replace("-", " ").replace("_", " ").strip().title()


def clean_text(value, max_len=160):
    """Collapse whitespace, truncate cleanly."""
    if isinstance(value, list):
        value = str(value[0]) if value else ""
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(value) <= max_len:
        return value
    return value[:max_len].rsplit(" ", 1)[0] + "…"


def xml_escape(value):
    return html_mod.escape(str(value), quote=True)


def normalize_keywords(raw, limit=12):
    """Deduplicate and cap a keyword list."""
    if isinstance(raw, str):
        raw = [k.strip() for k in raw.split(",") if k.strip()]
    if not isinstance(raw, list):
        return []
    seen = set()
    out = []
    for item in raw:
        k = str(item).strip()
        key = k.lower()
        if not k or key in seen or len(key) < 3:
            continue
        seen.add(key)
        out.append(k)
        if len(out) >= limit:
            break
    return out
