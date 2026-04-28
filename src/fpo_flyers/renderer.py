"""Render FPO flyers as HTML and PDF."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from .models import FPOEvent

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_html(event: FPOEvent, templates_dir: Path = TEMPLATES_DIR) -> str:
    """Render a flyer to HTML string (print layout for PDF conversion)."""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )
    template = env.get_template("flyer.html")
    return template.render(event=event)


def render_ipad_html(event: FPOEvent, templates_dir: Path = TEMPLATES_DIR) -> str:
    """Render a flyer to HTML string (iPad portrait layout)."""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )
    template = env.get_template("flyer_ipad.html")
    return template.render(event=event)


def render_pdf(
    event: FPOEvent,
    output_dir: Path,
    templates_dir: Path = TEMPLATES_DIR,
) -> Path:
    """Render a flyer to PDF and return the output path."""
    html_str = render_html(event, templates_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{event.safe_filename}.pdf"
    HTML(string=html_str).write_pdf(str(pdf_path))
    return pdf_path


def render_html_flyer(
    event: FPOEvent,
    output_dir: Path,
    templates_dir: Path = TEMPLATES_DIR,
) -> Path:
    """Render a flyer to a standalone HTML file (iPad portrait layout)."""
    html_str = render_ipad_html(event, templates_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{event.safe_filename}.html"
    html_path.write_text(html_str, encoding="utf-8")
    return html_path
