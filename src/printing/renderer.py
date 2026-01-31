"""Template renderer: Jinja2 HTML templates -> PNG images for thermal printing."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, BaseLoader

logger = logging.getLogger(__name__)

# Thermal printer width in pixels (72mm at ~203 DPI)
PRINTER_WIDTH_PX = 576

# Default template directories
BUNDLED_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "resources" / "templates"
USER_TEMPLATES_DIR = (
    Path.home() / "Library" / "Application Support" / "PrintDo" / "templates"
)


def _get_priority_dots(task_context: dict) -> str:
    """Generate priority indicator from task data."""
    tag_names = [t.lower() for t in task_context.get("tag_names", [])]

    # Check tags for priority keywords
    high_keywords = {"urgent", "critical", "important", "high", "asap", "priority"}
    low_keywords = {"low", "someday", "maybe", "optional"}

    if any(k in tag for tag in tag_names for k in high_keywords):
        return "\u26a1 \u26a1 \u26a1"
    if any(k in tag for tag in tag_names for k in low_keywords):
        return "\u26a1"
    return "\u26a1 \u26a1"


class TemplateRenderer:
    """Renders Things 3 tasks through Jinja2 HTML templates to PNG images."""

    def __init__(self):
        # Ensure user template dir exists
        USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment with multiple template dirs
        template_dirs = []
        if USER_TEMPLATES_DIR.exists():
            template_dirs.append(str(USER_TEMPLATES_DIR))
        if BUNDLED_TEMPLATES_DIR.exists():
            template_dirs.append(str(BUNDLED_TEMPLATES_DIR))

        self._env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=False,
        )

    def list_templates(self) -> list:
        """List all available template names."""
        templates = set()
        for d in [BUNDLED_TEMPLATES_DIR, USER_TEMPLATES_DIR]:
            if d.exists():
                for f in d.glob("*.html.j2"):
                    templates.add(f.stem.replace(".html", ""))
        return sorted(templates)

    def get_template_path(self, template_name: str) -> Optional[Path]:
        """Get the full path of a template by name."""
        filename = f"{template_name}.html.j2"
        # User templates take priority
        user_path = USER_TEMPLATES_DIR / filename
        if user_path.exists():
            return user_path
        bundled_path = BUNDLED_TEMPLATES_DIR / filename
        if bundled_path.exists():
            return bundled_path
        return None

    def get_template_source(self, template_name: str) -> str:
        """Read template source for editing."""
        path = self.get_template_path(template_name)
        if path:
            return path.read_text(encoding="utf-8")
        return ""

    def save_template(self, template_name: str, source: str) -> Path:
        """Save template source to user templates directory."""
        USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        path = USER_TEMPLATES_DIR / f"{template_name}.html.j2"
        path.write_text(source, encoding="utf-8")
        # Reload environment to pick up changes
        self.__init__()
        return path

    def render_html(self, task, template_name: str = "default") -> str:
        """Render a Things3Task into HTML using the given template."""
        from src.things3.models import Things3Task

        if isinstance(task, Things3Task):
            ctx = task.to_template_context()
        elif isinstance(task, dict):
            ctx = task
        else:
            ctx = {"name": str(task), "notes": "", "due_date": "", "tag_names": [], "project_name": "", "area_name": ""}

        priority_dots = _get_priority_dots(ctx)

        try:
            template = self._env.get_template(f"{template_name}.html.j2")
        except Exception:
            # Fallback to default template
            template = self._env.get_template("default.html.j2")

        return template.render(task=ctx, priority_dots=priority_dots)

    def render_to_png(self, task, template_name: str = "default") -> Optional[str]:
        """Render task to PNG image file suitable for thermal printing.

        Returns path to temporary PNG file, or None on failure.
        Uses PIL to render HTML to image (no external browser dependencies).
        """
        html = self.render_html(task, template_name)
        return self._html_to_png_pil(html)

    def _html_to_png_pil(self, html: str) -> Optional[str]:
        """Convert HTML to PNG using PIL as a simple fallback.

        This creates a clean text-based layout from the HTML content
        without needing a browser engine.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.error("PIL/Pillow not installed - cannot render template to PNG")
            return None

        try:
            # Parse key content from the rendered HTML (simple extraction)
            import re

            def extract_text(html_str, class_name):
                pattern = rf'class="{class_name}"[^>]*>(.*?)</(?:div|span|h1)'
                match = re.search(pattern, html_str, re.DOTALL)
                if match:
                    # Strip HTML tags
                    text = re.sub(r"<[^>]+>", "", match.group(1))
                    return text.strip()
                return ""

            # Try to extract structured content
            priority = extract_text(html, "priority-indicator") or extract_text(html, "priority")
            task_name = extract_text(html, "task-name")
            due_date = extract_text(html, "due-date")
            project = extract_text(html, "project-name") or extract_text(html, "project-label")
            notes = extract_text(html, "notes-text")

            # Extract tags
            tag_matches = re.findall(r'class="tag"[^>]*>([^<]+)</span>', html)
            tags = [t.strip() for t in tag_matches]

            if not priority:
                priority = "\u26a1 \u26a1"

            # Build image
            width = PRINTER_WIDTH_PX
            padding = 20
            y = padding

            # Prepare fonts
            try:
                # macOS fonts
                font_paths = [
                    "/System/Library/Fonts/SFNSDisplay.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "arial.ttf",
                ]
                title_font = None
                for fp in font_paths:
                    try:
                        title_font = ImageFont.truetype(fp, 42)
                        break
                    except (OSError, IOError):
                        continue

                if title_font is None:
                    title_font = ImageFont.load_default()

                small_font = None
                for fp in font_paths:
                    try:
                        small_font = ImageFont.truetype(fp, 18)
                        break
                    except (OSError, IOError):
                        continue

                if small_font is None:
                    small_font = ImageFont.load_default()

                medium_font = None
                for fp in font_paths:
                    try:
                        medium_font = ImageFont.truetype(fp, 24)
                        break
                    except (OSError, IOError):
                        continue

                if medium_font is None:
                    medium_font = ImageFont.load_default()

            except Exception:
                title_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                medium_font = ImageFont.load_default()

            # First pass: calculate height
            elements = []

            # Priority
            if priority:
                elements.append(("center", priority, medium_font, 10))

            # Project
            if project:
                elements.append(("center_small", project.upper(), small_font, 4))

            # Task name (wrapped)
            if task_name:
                import textwrap
                lines = textwrap.wrap(task_name, width=18)
                for line in lines:
                    elements.append(("center", line, title_font, 4))
                elements.append(("separator", "", None, 12))

            # Due date
            if due_date:
                elements.append(("center", due_date, medium_font, 8))

            # Tags
            if tags:
                elements.append(("tags", tags, small_font, 8))

            # Notes
            if notes:
                elements.append(("separator_thin", "", None, 8))
                import textwrap
                note_lines = textwrap.wrap(notes, width=50)
                for line in note_lines[:8]:  # Limit notes length
                    elements.append(("left", line, small_font, 3))

            # Perforation
            elements.append(("perforation", "", None, 12))

            # Calculate total height
            total_height = padding
            for elem_type, text, font, spacing in elements:
                if elem_type in ("separator", "separator_thin", "perforation"):
                    total_height += spacing + 6
                elif elem_type == "tags":
                    total_height += spacing + 28
                elif font:
                    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
                    total_height += (bbox[3] - bbox[1]) + spacing
                else:
                    total_height += spacing + 20
            total_height += padding

            # Create image
            img = Image.new("RGB", (width, total_height), "white")
            draw = ImageDraw.Draw(img)
            y = padding

            for elem_type, text, font, spacing in elements:
                if elem_type == "center" and font:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    tw = bbox[2] - bbox[0]
                    x = (width - tw) // 2
                    draw.text((x, y), text, fill="black", font=font)
                    y += (bbox[3] - bbox[1]) + spacing

                elif elem_type == "center_small" and font:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    tw = bbox[2] - bbox[0]
                    x = (width - tw) // 2
                    draw.text((x, y), text, fill="#555555", font=font)
                    y += (bbox[3] - bbox[1]) + spacing

                elif elem_type == "left" and font:
                    draw.text((padding, y), text, fill="#333333", font=font)
                    bbox = draw.textbbox((0, 0), text, font=font)
                    y += (bbox[3] - bbox[1]) + spacing

                elif elem_type == "separator":
                    y += spacing // 2
                    for x in range(padding, width - padding, 12):
                        draw.line([(x, y), (x + 6, y)], fill="#999999", width=2)
                    y += spacing // 2 + 6

                elif elem_type == "separator_thin":
                    y += spacing // 2
                    draw.line([(padding, y), (width - padding, y)], fill="#dddddd", width=1)
                    y += spacing // 2 + 6

                elif elem_type == "perforation":
                    y += spacing
                    for x in range(0, width, 12):
                        draw.rectangle([(x, y), (x + 6, y + 3)], fill="black")
                    y += 6

                elif elem_type == "tags":
                    tag_y = y
                    tag_x = padding
                    for tag_text in text:
                        bbox = draw.textbbox((0, 0), tag_text, font=font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        tag_w = tw + 16
                        tag_h = th + 8
                        if tag_x + tag_w > width - padding:
                            tag_x = padding
                            tag_y += tag_h + 4
                        draw.rectangle(
                            [(tag_x, tag_y), (tag_x + tag_w, tag_y + tag_h)],
                            fill="black",
                        )
                        draw.text(
                            (tag_x + 8, tag_y + 4), tag_text, fill="white", font=font
                        )
                        tag_x += tag_w + 6
                    y = tag_y + 28 + spacing

            # Save
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(temp.name, "PNG")
            temp.close()
            logger.info("Rendered template to PNG: %s", temp.name)
            return temp.name

        except Exception as e:
            logger.error("Failed to render template to PNG: %s", e)
            return None
