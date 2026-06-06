from .meta import build_meta
from .template import inject_meta, wrap_html


def build_page(meta: dict, body: str, template: str = None) -> str:
    meta_html = build_meta(meta)

    if template:
        return inject_meta(template, meta_html).replace("{{BODY}}", body)

    return wrap_html(body=body, meta=meta_html)
