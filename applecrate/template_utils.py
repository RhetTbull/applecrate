"""Utilities for working with templates"""

from __future__ import annotations

import os
import pathlib
from typing import Any, Callable

import markdown2
from jinja2 import Environment, PackageLoader, Template, select_autoescape

# extra features to support for Markdown to HTML conversion with markdown2
MARKDOWN_EXTRAS = ["fenced-code-blocks", "footnotes", "tables"]


def load_template_from_file(path: pathlib.Path) -> Template:
    """Load a Jinja2 template from a file."""
    with open(path) as file:
        return Template(file.read())


def get_template(name: str) -> Template:
    """Load a Jinja2 template from the package."""

    env = Environment(loader=PackageLoader("applecrate", "templates"), autoescape=select_autoescape())
    return env.get_template(name)


def render_markdown_template(template: Template, data: dict[str, str], output: pathlib.Path):
    """Render and save a Jinja2 template to a file, converting markdown to HTML."""
    md = template.render(**data)
    html = markdown2.markdown(md, extras=MARKDOWN_EXTRAS)
    head = (
        '<head> <meta charset="utf-8" /> <style> body { font-family: Helvetica, sans-serif; font-size: 14px; } </style> </head>'
    )
    html = f"<!DOCTYPE html>\n<html>\n{head}\n<body>\n{html}\n</body>\n</html>"
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as file:
        file.write(html)


def render_template(template: Template, data: dict[str, Any], output: pathlib.Path):
    """Render and save a Jinja2 template to a file."""
    rendered = template.render(**data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as file:
        file.write(rendered)


def render_template_from_file(filepath: pathlib.Path, data: dict[str, Any], output: pathlib.Path):
    """Render and save a Jinja2 template to a file."""
    template = load_template_from_file(filepath)
    rendered = template.render(**data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as file:
        file.write(rendered)


def create_html_file(
    input_path: pathlib.Path | None,
    output_path: pathlib.Path,
    data: dict[str, str],
    default_template: str,
    verbose: Callable[..., None],
):
    """Create an HTML file from a markdown or HTML file and render with Jinja2."""

    if input_path:
        template = load_template_from_file(input_path)
    else:
        template = get_template(default_template)

    if not input_path or input_path.suffix.lower() in [".md", ".markdown"]:
        # passed a markdown file or no file at all
        render_markdown_template(template, data, output_path)
    else:
        render_template(template, data, output_path)

    verbose(f"Created {output_path}")
