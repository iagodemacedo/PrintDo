"""Print preview widget showing rendered task card."""

import logging
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from src.printing.renderer import TemplateRenderer
from src.things3.models import Things3Task

logger = logging.getLogger(__name__)


class PreviewWidget(QWidget):
    """Shows a live preview of the task card as it would print."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = TemplateRenderer()
        self._current_template = "default"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for the preview image
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f5f5f7; }")

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._image_label.setStyleSheet("background: transparent; padding: 12px;")
        self._image_label.setText("Select a task to preview")

        scroll.setWidget(self._image_label)
        layout.addWidget(scroll)

    def set_template(self, template_name: str):
        """Change the template used for rendering."""
        self._current_template = template_name

    def preview_task(self, task: Things3Task):
        """Render and display a task preview."""
        try:
            png_path = self._renderer.render_to_png(task, self._current_template)
            if png_path:
                pixmap = QPixmap(png_path)
                # Scale to fit width while maintaining aspect ratio
                max_width = min(self.width() - 40, 576)
                if pixmap.width() > max_width:
                    pixmap = pixmap.scaledToWidth(
                        max_width, Qt.TransformationMode.SmoothTransformation
                    )
                self._image_label.setPixmap(pixmap)
            else:
                self._image_label.setText("Failed to render preview")
        except Exception as e:
            logger.error("Preview render failed: %s", e)
            self._image_label.setText(f"Preview error: {e}")

    def preview_html(self, html: str):
        """Preview arbitrary HTML (used by template editor)."""
        try:
            png_path = self._renderer._html_to_png_pil(html)
            if png_path:
                pixmap = QPixmap(png_path)
                max_width = min(self.width() - 40, 576)
                if pixmap.width() > max_width:
                    pixmap = pixmap.scaledToWidth(
                        max_width, Qt.TransformationMode.SmoothTransformation
                    )
                self._image_label.setPixmap(pixmap)
            else:
                self._image_label.setText("Failed to render preview")
        except Exception as e:
            self._image_label.setText(f"Preview error: {e}")

    def clear_preview(self):
        self._image_label.clear()
        self._image_label.setText("Select a task to preview")
