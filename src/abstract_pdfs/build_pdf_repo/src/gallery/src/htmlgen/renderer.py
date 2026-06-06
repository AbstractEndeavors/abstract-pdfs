from pathlib import Path
from .builder import build_page


def render_to_file(meta: dict, body: str, out_path: str, template_path: str = None):
    template = None

    if template_path:
        template = Path(template_path).read_text()

    html = build_page(meta=meta, body=body, template=template)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html)
