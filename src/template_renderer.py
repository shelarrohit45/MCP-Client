"""Render Jinja2 email templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"


class TemplateRenderError(Exception):
    """Raised when a template cannot be loaded or rendered."""


def render_template(template_name: str, **context: object) -> str:
    """Load and render an HTML template from the templates/ directory."""
    if not TEMPLATES_DIR.is_dir():
        raise TemplateRenderError(f"Templates directory not found: {TEMPLATES_DIR}")

    template_path = TEMPLATES_DIR / template_name
    if not template_path.is_file():
        raise TemplateRenderError(f"Template not found: {template_path}")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )
    return env.get_template(template_name).render(**context)
