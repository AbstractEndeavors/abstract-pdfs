from .imports import *
# ═══════════════════════════════════════════════════════════════
# Template registry
# ═══════════════════════════════════════════════════════════════


class TemplateRegistry:
    """
    Loads and caches Jinja2 templates from a directory.
    Templates are registered by name, not discovered at runtime.
    """

    KNOWN_TEMPLATES = frozenset({"viewer", "gallery", "image_page", "page_viewer", "page_seo"})

    def __init__(self, template_dir: Path) -> None:
        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(default_for_string=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Validate all known templates exist at init time, not render time
        for name in self.KNOWN_TEMPLATES:
            filename = f"{name}.html.j2"
            try:
                self._env.get_template(filename)
            except Exception as exc:
                raise FileNotFoundError(
                    f"Required template '{filename}' not found in {template_dir}"
                ) from exc

    def render(self, template_name: str, **ctx: Any) -> str:
        if template_name not in self.KNOWN_TEMPLATES:
            raise ValueError(
                f"Unknown template '{template_name}'. "
                f"Known: {sorted(self.KNOWN_TEMPLATES)}"
            )
        tmpl = self._env.get_template(f"{template_name}.html.j2")
        return tmpl.render(**ctx)



