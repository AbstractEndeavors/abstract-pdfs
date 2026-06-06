"""
Standalone HTML assembly.

For cases where you have a body string and meta dict but no Jinja2 template —
produces a complete <!DOCTYPE html> page with CSS links.
"""
from __future__ import annotations

from .meta.seo import build_seo_html


SHELL = """\
<!DOCTYPE html>
<html lang="en">
<head>
{meta}

<link rel="stylesheet" href="/assets/css/base.css">
<link rel="stylesheet" href="/assets/css/layout.css">
<link rel="stylesheet" href="/assets/css/components.css">
</head>
<body>
{body}
</body>
</html>
"""


def build_standalone_page(meta_dict, body_html, template_html=None):
    """
    Build a complete HTML page.

    If *template_html* is supplied it must contain ``{{SEO_META}}`` and
    ``{{BODY}}`` placeholders which are replaced directly.

    Otherwise, the default SHELL is used.
    """
    meta_html = build_seo_html(meta_dict)

    if template_html:
        if "{{SEO_META}}" not in template_html:
            raise ValueError("Template missing {{SEO_META}} placeholder")
        html = template_html.replace("{{SEO_META}}", meta_html.strip())
        html = html.replace("{{BODY}}", body_html)
        return html

    return SHELL.format(meta=meta_html, body=body_html)
