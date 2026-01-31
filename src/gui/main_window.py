"""Main application window for PrintDo."""

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from src.database.local_state import PrintStateDB
from src.gui.preview_widget import PreviewWidget
from src.gui.styles import TASK_ITEM_STYLE
from src.gui.task_list_widget import TaskListWidget
from src.printing.printer_manager import PrinterManager
from src.printing.renderer import TemplateRenderer
from src.things3.bridge import Things3Bridge
from src.things3.models import Things3Task
from src.things3.poller import Things3Poller

logger = logging.getLogger(__name__)


class FetchWorker(QObject):
    """Worker to fetch tasks from Things 3 in a background thread."""

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, bridge: Things3Bridge):
        super().__init__()
        self._bridge = bridge

    def run(self):
        try:
            tasks = self._bridge.get_today_tasks()
            self.finished.emit(tasks)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """PrintDo main window with task list, preview, and controls."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrintDo")
        self.setMinimumSize(700, 560)
        self.resize(820, 640)

        # Core components
        self._bridge = Things3Bridge()
        self._state_db = PrintStateDB()
        self._renderer = TemplateRenderer()
        self._printer_manager = PrinterManager()
        self._poller: Optional[Things3Poller] = None
        self._current_template = self._state_db.get_pref("default_template", "default")

        self._build_ui()
        self._connect_signals()

        # Load initial tasks
        self._refresh_tasks()

    def _build_ui(self):
        # --- Toolbar ---
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        # Auto-print toggle
        self._auto_print_btn = QPushButton("Auto-Print")
        self._auto_print_btn.setObjectName("toggleBtn")
        self._auto_print_btn.setCheckable(True)
        self._auto_print_btn.setChecked(False)
        toolbar.addWidget(self._auto_print_btn)

        toolbar.addSeparator()

        # Template selector
        toolbar.addWidget(QLabel("  Template: "))
        self._template_combo = QComboBox()
        self._template_combo.setMinimumWidth(120)
        templates = self._renderer.list_templates()
        self._template_combo.addItems(templates)
        idx = self._template_combo.findText(self._current_template)
        if idx >= 0:
            self._template_combo.setCurrentIndex(idx)
        toolbar.addWidget(self._template_combo)

        # Spacer
        spacer = QWidget()
        spacer.setFixedWidth(12)
        toolbar.addWidget(spacer)

        # Refresh button
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setObjectName("secondaryBtn")
        self._refresh_btn.setFixedWidth(80)
        toolbar.addWidget(self._refresh_btn)

        # Settings button
        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setObjectName("secondaryBtn")
        self._settings_btn.setFixedWidth(80)
        toolbar.addWidget(self._settings_btn)

        # --- Central widget ---
        central = QWidget()
        central.setStyleSheet(TASK_ITEM_STYLE)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Tab-like header
        from PySide6.QtWidgets import QTabWidget

        self._tabs = QTabWidget()

        # --- Tasks tab ---
        tasks_widget = QWidget()
        tasks_layout = QVBoxLayout(tasks_widget)
        tasks_layout.setContentsMargins(8, 8, 8, 8)
        tasks_layout.setSpacing(8)

        # Task list header
        header_row = QHBoxLayout()
        title_label = QLabel("Today's Tasks")
        title_label.setObjectName("sectionTitle")
        header_row.addWidget(title_label)

        self._task_count_label = QLabel("")
        self._task_count_label.setObjectName("subtitle")
        header_row.addWidget(self._task_count_label)

        header_row.addStretch()

        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.setObjectName("secondaryBtn")
        self._select_all_btn.setFixedWidth(90)
        header_row.addWidget(self._select_all_btn)

        tasks_layout.addLayout(header_row)

        # Splitter: task list (top) + preview (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        self._task_list = TaskListWidget()
        splitter.addWidget(self._task_list)

        self._preview = PreviewWidget()
        splitter.addWidget(self._preview)

        splitter.setSizes([320, 240])
        tasks_layout.addWidget(splitter)

        # Print button row
        print_row = QHBoxLayout()
        print_row.addStretch()

        self._print_selected_btn = QPushButton("Print Selected")
        self._print_selected_btn.setFixedWidth(140)
        print_row.addWidget(self._print_selected_btn)

        self._print_all_btn = QPushButton("Print All")
        self._print_all_btn.setObjectName("secondaryBtn")
        self._print_all_btn.setFixedWidth(100)
        print_row.addWidget(self._print_all_btn)

        tasks_layout.addLayout(print_row)

        self._tabs.addTab(tasks_widget, "Tasks")

        # --- Template Editor tab ---
        from src.gui.template_editor import TemplateEditor

        self._template_editor = TemplateEditor()
        self._tabs.addTab(self._template_editor, "Template Editor")

        main_layout.addWidget(self._tabs)

        # --- Status bar ---
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        self._status_bar.addWidget(self._status_label)

    def _connect_signals(self):
        self._refresh_btn.clicked.connect(self._refresh_tasks)
        self._auto_print_btn.toggled.connect(self._toggle_auto_print)
        self._print_selected_btn.clicked.connect(self._print_selected)
        self._print_all_btn.clicked.connect(self._print_all)
        self._select_all_btn.clicked.connect(self._toggle_select_all)
        self._settings_btn.clicked.connect(self._open_preferences)
        self._task_list.task_selected.connect(self._on_task_selected)
        self._template_combo.currentTextChanged.connect(self._on_template_changed)

    # --- Task fetching ---

    def _refresh_tasks(self):
        """Fetch tasks from Things 3 in a background thread."""
        self._status_label.setText("Fetching tasks from Things 3...")
        self._refresh_btn.setEnabled(False)

        self._fetch_thread = QThread()
        self._fetch_worker = FetchWorker(self._bridge)
        self._fetch_worker.moveToThread(self._fetch_thread)
        self._fetch_thread.started.connect(self._fetch_worker.run)
        self._fetch_worker.finished.connect(self._on_tasks_fetched)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.finished.connect(self._fetch_thread.quit)
        self._fetch_worker.error.connect(self._fetch_thread.quit)
        self._fetch_thread.start()

    def _on_tasks_fetched(self, tasks: List[Things3Task]):
        self._task_list.set_tasks(tasks)
        count = self._task_list.task_count
        self._task_count_label.setText(f"{count} task{'s' if count != 1 else ''}")
        self._status_label.setText(f"Loaded {count} tasks from Things 3")
        self._refresh_btn.setEnabled(True)

        # Mark all as seen
        for task in tasks:
            self._state_db.mark_seen(task.id, task.name)

    def _on_fetch_error(self, error: str):
        self._status_label.setText(f"Error: {error}")
        self._refresh_btn.setEnabled(True)
        logger.error("Fetch error: %s", error)

    # --- Task selection & preview ---

    def _on_task_selected(self, task: Things3Task):
        self._preview.set_template(self._current_template)
        self._preview.preview_task(task)

    def _on_template_changed(self, name: str):
        self._current_template = name
        self._preview.set_template(name)
        self._state_db.set_pref("default_template", name)

    def _toggle_select_all(self):
        checked = self._task_list.get_checked_tasks()
        if checked:
            self._task_list.deselect_all()
            self._select_all_btn.setText("Select All")
        else:
            self._task_list.select_all()
            self._select_all_btn.setText("Deselect All")

    # --- Printing ---

    def _print_tasks(self, tasks: List[Things3Task]):
        """Print a list of tasks."""
        if not tasks:
            self._status_label.setText("No tasks to print")
            return

        printed = 0
        errors = 0

        for task in tasks:
            png_path = self._renderer.render_to_png(task, self._current_template)
            if png_path:
                success = self._printer_manager.print_image(png_path)
                if success:
                    self._state_db.mark_printed(task.id, task.name, self._current_template)
                    printed += 1
                else:
                    errors += 1
            else:
                errors += 1

        status = f"Printed {printed} task{'s' if printed != 1 else ''}"
        if errors:
            status += f" ({errors} failed)"
        self._status_label.setText(status)

    def _print_selected(self):
        tasks = self._task_list.get_checked_tasks()
        if not tasks:
            self._status_label.setText("No tasks selected")
            return
        self._print_tasks(tasks)

    def _print_all(self):
        tasks = self._task_list.get_all_tasks()
        self._print_tasks(tasks)

    # --- Auto-print ---

    def _toggle_auto_print(self, enabled: bool):
        if enabled:
            self._start_poller()
        else:
            self._stop_poller()

    def _start_poller(self):
        interval = int(self._state_db.get_pref("poll_interval", "30")) * 1000
        self._poller = Things3Poller(self._bridge, interval_ms=interval)

        # Seed with already-printed task IDs to avoid re-printing
        seen_ids = self._state_db.get_all_seen_ids()
        self._poller.seed_seen_ids(seen_ids)

        self._poller.new_tasks_found.connect(self._on_auto_print_tasks)
        self._poller.poll_completed.connect(self._on_poll_completed)
        self._poller.poll_error.connect(self._on_poll_error)
        self._poller.start()

        self._status_label.setText("Auto-print enabled")
        logger.info("Auto-print started")

    def _stop_poller(self):
        if self._poller:
            self._poller.stop()
            self._poller.wait(5000)
            self._poller = None
        self._status_label.setText("Auto-print disabled")
        logger.info("Auto-print stopped")

    def _on_auto_print_tasks(self, new_tasks: List[Things3Task]):
        """Handle new tasks detected by the poller."""
        self._status_label.setText(f"Auto-printing {len(new_tasks)} new task(s)...")

        for task in new_tasks:
            if not self._state_db.is_printed(task.id):
                png_path = self._renderer.render_to_png(task, self._current_template)
                if png_path:
                    success = self._printer_manager.print_image(png_path)
                    if success:
                        self._state_db.mark_printed(task.id, task.name, self._current_template)
                        logger.info("Auto-printed: %s", task.name)

        # Refresh the task list to show new tasks
        self._refresh_tasks()

    def _on_poll_completed(self, count: int):
        if self._auto_print_btn.isChecked():
            self._status_label.setText(f"Auto-print active | {count} tasks in Today")

    def _on_poll_error(self, error: str):
        self._status_label.setText(f"Poll error: {error}")

    # --- Preferences ---

    def _open_preferences(self):
        from src.gui.preferences_dialog import PreferencesDialog

        dialog = PreferencesDialog(self._state_db, parent=self)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self):
        """Apply changed settings."""
        # Update template
        template = self._state_db.get_pref("default_template", "default")
        self._current_template = template
        idx = self._template_combo.findText(template)
        if idx >= 0:
            self._template_combo.setCurrentIndex(idx)

        # Update poller interval if running
        if self._poller:
            interval = int(self._state_db.get_pref("poll_interval", "30")) * 1000
            self._poller.set_interval(interval)

    # --- Cleanup ---

    def closeEvent(self, event):
        self._stop_poller()
        self._state_db.close()
        super().closeEvent(event)
