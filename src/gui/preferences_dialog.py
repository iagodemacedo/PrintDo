"""Preferences dialog for PrintDo application settings."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.database.local_state import PrintStateDB
from src.gui.printer_settings import PrinterSettingsWidget
from src.printing.renderer import TemplateRenderer

logger = logging.getLogger(__name__)


class PreferencesDialog(QDialog):
    """Application preferences dialog."""

    settings_changed = Signal()

    def __init__(self, state_db: PrintStateDB, parent=None):
        super().__init__(parent)
        self._db = state_db
        self._renderer = TemplateRenderer()
        self.setWindowTitle("PrintDo Preferences")
        self.setMinimumSize(520, 420)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()

        # --- General tab ---
        general_tab = QWidget()
        gen_layout = QVBoxLayout(general_tab)
        gen_layout.setSpacing(16)

        # Polling interval
        poll_group = QGroupBox("Auto-Print")
        poll_layout = QFormLayout(poll_group)

        interval_row = QHBoxLayout()
        self._interval_slider = QSlider(Qt.Orientation.Horizontal)
        self._interval_slider.setRange(10, 300)
        self._interval_slider.setValue(30)
        self._interval_slider.setTickInterval(30)
        self._interval_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._interval_slider.valueChanged.connect(self._on_interval_changed)
        interval_row.addWidget(self._interval_slider)

        self._interval_label = QLabel("30s")
        self._interval_label.setFixedWidth(50)
        interval_row.addWidget(self._interval_label)

        poll_layout.addRow("Poll Interval:", interval_row)
        gen_layout.addWidget(poll_group)

        # Default template
        template_group = QGroupBox("Printing")
        tmpl_layout = QFormLayout(template_group)

        self._template_combo = QComboBox()
        templates = self._renderer.list_templates()
        self._template_combo.addItems(templates)
        tmpl_layout.addRow("Default Template:", self._template_combo)

        gen_layout.addWidget(template_group)
        gen_layout.addStretch()

        tabs.addTab(general_tab, "General")

        # --- Printer tab ---
        self._printer_settings = PrinterSettingsWidget()
        tabs.addTab(self._printer_settings, "Printer")

        # --- API Keys tab ---
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        api_layout.setSpacing(16)

        api_group = QGroupBox("API Keys (for Arcade / AI features)")
        api_form = QFormLayout(api_group)

        self._arcade_key_input = QLineEdit()
        self._arcade_key_input.setPlaceholderText("Enter Arcade API key...")
        self._arcade_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("Arcade API Key:", self._arcade_key_input)

        self._openai_key_input = QLineEdit()
        self._openai_key_input.setPlaceholderText("Enter OpenAI API key...")
        self._openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("OpenAI API Key:", self._openai_key_input)

        self._arcade_user_input = QLineEdit()
        self._arcade_user_input.setPlaceholderText("your@email.com")
        api_form.addRow("Arcade User ID:", self._arcade_user_input)

        api_layout.addWidget(api_group)
        api_layout.addStretch()

        tabs.addTab(api_tab, "API Keys")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_interval_changed(self, value: int):
        self._interval_label.setText(f"{value}s")

    def _load_settings(self):
        interval = int(self._db.get_pref("poll_interval", "30"))
        self._interval_slider.setValue(interval)
        self._interval_label.setText(f"{interval}s")

        template = self._db.get_pref("default_template", "default")
        idx = self._template_combo.findText(template)
        if idx >= 0:
            self._template_combo.setCurrentIndex(idx)

        self._arcade_key_input.setText(self._db.get_pref("arcade_api_key", ""))
        self._openai_key_input.setText(self._db.get_pref("openai_api_key", ""))
        self._arcade_user_input.setText(self._db.get_pref("arcade_user_id", ""))

    def _save_and_accept(self):
        self._db.set_pref("poll_interval", str(self._interval_slider.value()))
        self._db.set_pref("default_template", self._template_combo.currentText())
        self._db.set_pref("arcade_api_key", self._arcade_key_input.text())
        self._db.set_pref("openai_api_key", self._openai_key_input.text())
        self._db.set_pref("arcade_user_id", self._arcade_user_input.text())
        self.settings_changed.emit()
        self.accept()

    @property
    def poll_interval_seconds(self) -> int:
        return self._interval_slider.value()

    @property
    def default_template(self) -> str:
        return self._template_combo.currentText()
