"""Template editor with live preview and variable reference."""

import logging
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QInputDialog,
)

from src.gui.preview_widget import PreviewWidget
from src.printing.renderer import TemplateRenderer
from src.things3.models import Things3Task

logger = logging.getLogger(__name__)

# Sample task for preview
SAMPLE_TASK = Things3Task(
    id="sample-001",
    name="Review quarterly report",
    notes="Check all figures and update charts for Q4.\nSend to team by Friday.",
    due_date=datetime.now(),
    tag_names=["Work", "Urgent"],
    project_name="Q4 Planning",
    area_name="Business",
    status="open",
    creation_date=datetime.now(),
    modification_date=datetime.now(),
)

VARIABLE_REFERENCE = """<b>Available Template Variables:</b><br><br>
<code>{{ task.name }}</code> - Task title<br>
<code>{{ task.notes }}</code> - Task description/notes<br>
<code>{{ task.due_date }}</code> - Formatted deadline (e.g., "January 31st")<br>
<code>{{ task.due_date_short }}</code> - Short date (e.g., "Jan 31")<br>
<code>{{ task.tag_names }}</code> - List of tags<br>
<code>{{ task.tags_display }}</code> - Tags as comma-separated string<br>
<code>{{ task.project_name }}</code> - Project name<br>
<code>{{ task.area_name }}</code> - Area name<br>
<code>{{ task.status }}</code> - Status (open/completed/canceled)<br>
<code>{{ priority_dots }}</code> - Priority indicator (lightning bolts)<br><br>
<b>Jinja2 Conditionals:</b><br>
<code>{% if task.project_name %}...{% endif %}</code><br>
<code>{% for tag in task.tag_names %}...{% endfor %}</code>
"""


class TemplateEditor(QWidget):
    """Editor for customizing print templates with live preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = TemplateRenderer()
        self._current_template = "default"
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(500)
        self._debounce_timer.timeout.connect(self._update_preview)
        self._build_ui()
        self._load_template("default")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top bar: template selector + actions
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        top_bar.addWidget(QLabel("Template:"))
        self._template_combo = QComboBox()
        self._template_combo.setMinimumWidth(160)
        self._refresh_template_list()
        self._template_combo.currentTextChanged.connect(self._on_template_changed)
        top_bar.addWidget(self._template_combo)

        self._save_btn = QPushButton("Save")
        self._save_btn.setFixedWidth(80)
        self._save_btn.clicked.connect(self._save_template)
        top_bar.addWidget(self._save_btn)

        self._save_as_btn = QPushButton("Save As...")
        self._save_as_btn.setObjectName("secondaryBtn")
        self._save_as_btn.setFixedWidth(100)
        self._save_as_btn.clicked.connect(self._save_as_template)
        top_bar.addWidget(self._save_as_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Main content: editor | preview (horizontal split)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: code editor + variable reference
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("Enter Jinja2 HTML template...")
        self._editor.textChanged.connect(self._on_text_changed)
        left_layout.addWidget(self._editor, stretch=3)

        # Variable reference panel
        ref_label = QLabel("Variable Reference")
        ref_label.setObjectName("sectionTitle")
        left_layout.addWidget(ref_label)

        ref_text = QTextEdit()
        ref_text.setReadOnly(True)
        ref_text.setHtml(VARIABLE_REFERENCE)
        ref_text.setMaximumHeight(200)
        ref_text.setStyleSheet(
            "QTextEdit { background: #f5f5f7; border: 1px solid #d2d2d7; "
            "border-radius: 6px; padding: 8px; font-size: 12px; color: #1d1d1f; }"
        )
        left_layout.addWidget(ref_text, stretch=1)

        splitter.addWidget(left_widget)

        # Right side: preview
        self._preview = PreviewWidget()
        splitter.addWidget(self._preview)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter)

    def _refresh_template_list(self):
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        templates = self._renderer.list_templates()
        self._template_combo.addItems(templates)
        # Set current
        idx = self._template_combo.findText(self._current_template)
        if idx >= 0:
            self._template_combo.setCurrentIndex(idx)
        self._template_combo.blockSignals(False)

    def _on_template_changed(self, name: str):
        if name:
            self._load_template(name)

    def _load_template(self, name: str):
        self._current_template = name
        source = self._renderer.get_template_source(name)
        self._editor.blockSignals(True)
        self._editor.setPlainText(source)
        self._editor.blockSignals(False)
        self._update_preview()

    def _on_text_changed(self):
        self._debounce_timer.start()

    def _update_preview(self):
        """Re-render the preview with current editor content and sample task."""
        source = self._editor.toPlainText()
        if not source.strip():
            return

        try:
            from jinja2 import Environment, BaseLoader

            env = Environment(loader=BaseLoader(), autoescape=False)
            template = env.from_string(source)
            ctx = SAMPLE_TASK.to_template_context()
            from src.printing.renderer import _get_priority_dots
            html = template.render(task=ctx, priority_dots=_get_priority_dots(ctx))
            self._preview.preview_html(html)
        except Exception as e:
            logger.debug("Template render error (may be incomplete edit): %s", e)

    def _save_template(self):
        source = self._editor.toPlainText()
        name = self._current_template
        self._renderer.save_template(name, source)
        self._refresh_template_list()

    def _save_as_template(self):
        name, ok = QInputDialog.getText(
            self, "Save Template As", "Template name:",
            text=self._current_template + "_copy"
        )
        if ok and name:
            name = name.replace(" ", "_").lower()
            source = self._editor.toPlainText()
            self._renderer.save_template(name, source)
            self._current_template = name
            self._refresh_template_list()

    def get_current_template_name(self) -> str:
        return self._current_template
