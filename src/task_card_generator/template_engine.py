"""Jinja2-based template engine for task card rendering."""

import json
import os

from jinja2 import BaseLoader, Environment, FileSystemLoader

from .config import CUSTOM_TEMPLATES_DIR

# ---------------------------------------------------------------------------
# Block system — maps block types to Jinja2 HTML snippets
# ---------------------------------------------------------------------------

DEFAULT_STYLE = {
    "title_size": 34,
    "body_size": 15,
    "due_date_size": 22,
    "render_width": 576,
    "print_scale": 2,
    "top_margin": 0,
    "bottom_margin": 2,
}


def _build_css(style: dict) -> str:
    """Build template CSS with the given style parameters."""
    s = {**DEFAULT_STYLE, **(style or {})}
    meta_size = max(int(s["body_size"] * 1.13), s["body_size"] + 1)
    tag_size = s["body_size"]
    return f"""\
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, 'Helvetica Neue', Helvetica, sans-serif;
        background: white;
        width: {s["render_width"]}px;
        color: #111;
    }}
    .card {{
        padding: 8px 16px;
    }}
    .title {{
        font-size: {s["title_size"]}px;
        font-weight: 700;
        text-align: center;
        line-height: 1.2;
        margin-bottom: 14px;
        word-wrap: break-word;
    }}
    .sep {{
        border: none;
        border-top: 2px dashed #bbb;
        margin: 10px 0;
    }}
    .meta {{
        font-size: {meta_size}px;
        color: #333;
        margin: 5px 0;
    }}
    .meta-label {{
        font-weight: 600;
    }}
    .tags {{
        margin: 8px 0;
    }}
    .tag {{
        display: inline-block;
        border: 1.5px solid #888;
        border-radius: 4px;
        padding: 2px 10px;
        margin: 2px 3px;
        font-size: {tag_size}px;
        color: #555;
    }}
    .notes {{
        font-size: {s["body_size"]}px;
        color: #444;
        margin-top: 8px;
        white-space: pre-wrap;
        line-height: 1.4;
    }}
    .due-date {{
        font-size: {s["due_date_size"]}px;
        font-weight: 600;
        text-align: center;
        margin-top: 10px;
    }}
    .checklist-item {{
        font-size: {s["body_size"] + 1}px;
        margin: 3px 0;
        color: #333;
    }}
    .checklist-item::before {{
        content: "\\2610  ";
    }}"""

BLOCK_SNIPPETS = {
    "title": '<div class="title">{{ task.name }}</div>',
    "separator": '<hr class="sep">',
    "project": (
        '{% if task.project %}\n'
        '    <div class="meta"><span class="meta-label">Project:</span> '
        '{{ task.project }}</div>\n'
        '    {% endif %}'
    ),
    "due_date": (
        '{% if task.due_date %}\n'
        '    <div class="due-date">{{ task.due_date }}</div>\n'
        '    {% endif %}'
    ),
    "tags": (
        '{% if task.tags %}\n'
        '    <div class="tags">\n'
        '        {% for tag in task.tags %}\n'
        '        <span class="tag">{{ tag }}</span>\n'
        '        {% endfor %}\n'
        '    </div>\n'
        '    {% endif %}'
    ),
    "notes": (
        '{% if task.notes %}\n'
        '    <div class="notes">{{ task.notes }}</div>\n'
        '    {% endif %}'
    ),
}


def get_default_blocks_config():
    """Return the default block configuration (with style)."""
    return {
        "blocks": [
            {"type": "title", "enabled": True},
            {"type": "separator", "enabled": True, "id": "sep-1"},
            {"type": "project", "enabled": True},
            {"type": "due_date", "enabled": True},
            {"type": "tags", "enabled": True},
            {"type": "separator", "enabled": True, "id": "sep-2"},
            {"type": "notes", "enabled": True},
        ],
        "style": dict(DEFAULT_STYLE),
    }


def generate_template_from_blocks(config):
    """Generate a full Jinja2 HTML template from a block + style config.

    Args:
        config: Either a dict ``{"blocks": [...], "style": {...}}``
                or a plain list of blocks (legacy, uses default style).

    Returns:
        Complete HTML template string ready for Jinja2 rendering.
    """
    if isinstance(config, dict):
        blocks = config.get("blocks", [])
        style = config.get("style")
    else:
        blocks = config
        style = None

    parts = []
    for block in blocks:
        if not block.get("enabled", True):
            continue
        snippet = BLOCK_SNIPPETS.get(block["type"])
        if snippet:
            parts.append(snippet)

    body = "\n\n    ".join(parts)
    css = _build_css(style)
    width = (style or DEFAULT_STYLE).get("render_width", 576)

    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '<meta charset="UTF-8">\n'
        "<style>\n"
        f"{css}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="card">\n'
        f"    {body}\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------------------------------
# Template engine class
# ---------------------------------------------------------------------------

class TemplateEngine:
    """Render Things 3 tasks into HTML using Jinja2 templates."""

    BUILTIN_DIR = os.path.join(os.path.dirname(__file__), "templates")

    def __init__(self, custom_template_path: str = None):
        self.custom_template_path = custom_template_path
        self._setup_env()

    @staticmethod
    def _custom_html_path():
        return os.path.join(CUSTOM_TEMPLATES_DIR, "custom.html")

    def _setup_env(self):
        """Configure the Jinja2 environment, preferring custom template."""
        path = self.custom_template_path or self._custom_html_path()
        if os.path.isfile(path):
            self.env = Environment(
                loader=FileSystemLoader(os.path.dirname(path))
            )
            self.template_name = os.path.basename(path)
        else:
            self.env = Environment(
                loader=FileSystemLoader(self.BUILTIN_DIR)
            )
            self.template_name = "default.html"

    def get_style(self) -> dict:
        """Return the saved style dict (with defaults filled in)."""
        config = self.load_blocks_config()
        return {**DEFAULT_STYLE, **(config.get("style") or {})}

    def get_render_width(self) -> int:
        return self.get_style()["render_width"]

    def get_print_scale(self) -> int:
        return self.get_style().get("print_scale", 2)

    def get_margins(self) -> tuple:
        """Return ``(top_margin, bottom_margin)`` in feed lines."""
        s = self.get_style()
        return s.get("top_margin", 0), s.get("bottom_margin", 2)

    def render(self, task) -> str:
        """Render a Things3Task (or dict) into HTML string.

        Re-checks for custom.html each time so edits from the
        template editor take effect without restarting.
        """
        self._setup_env()
        template = self.env.get_template(self.template_name)
        return template.render(task=task)

    def render_from_string(self, template_str: str, task) -> str:
        """Render from a raw template string (for live preview in editor)."""
        env = Environment(loader=BaseLoader())
        template = env.from_string(template_str)
        return template.render(task=task)

    def get_template_source(self) -> str:
        """Return the current template source for editing."""
        source, _, _ = self.env.loader.get_source(self.env, self.template_name)
        return source

    def get_default_template_source(self) -> str:
        """Return the built-in default template source."""
        default_path = os.path.join(self.BUILTIN_DIR, "default.html")
        with open(default_path, "r") as f:
            return f.read()

    # --- Block config persistence ---

    @staticmethod
    def _blocks_json_path():
        return os.path.join(CUSTOM_TEMPLATES_DIR, "blocks.json")

    def load_blocks_config(self):
        """Load block configuration from ``blocks.json``, or return defaults.

        Always returns ``{"blocks": [...], "style": {...}}``.
        """
        path = self._blocks_json_path()
        if os.path.isfile(path):
            with open(path, "r") as f:
                data = json.load(f)
            # Migrate legacy format (plain list)
            if isinstance(data, list):
                data = {"blocks": data, "style": dict(DEFAULT_STYLE)}
            if "style" not in data:
                data["style"] = dict(DEFAULT_STYLE)
            return data
        return get_default_blocks_config()

    def save_blocks_config(self, config):
        """Persist *config* as JSON **and** regenerate ``custom.html``.

        Args:
            config: ``{"blocks": [...], "style": {...}}``.
        """
        os.makedirs(CUSTOM_TEMPLATES_DIR, exist_ok=True)

        with open(self._blocks_json_path(), "w") as f:
            json.dump(config, f, indent=2)

        html = generate_template_from_blocks(config)
        with open(os.path.join(CUSTOM_TEMPLATES_DIR, "custom.html"), "w") as f:
            f.write(html)
