def inject_meta(template: str, meta: str) -> str:
    if "{{SEO_META}}" not in template:
        raise ValueError("Missing {{SEO_META}} placeholder")
    return template.replace("{{SEO_META}}", meta.strip())


def wrap_html(body: str, meta: str) -> str:
    return f"""<!DOCTYPE html>
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
