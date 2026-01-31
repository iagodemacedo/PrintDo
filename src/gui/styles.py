"""QSS Stylesheets for PrintDo - clean, minimal macOS design."""

MAIN_STYLESHEET = """
/* Global */
QWidget {
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: #1d1d1f;
}

QMainWindow {
    background-color: #fafafa;
}

/* Toolbar */
QToolBar {
    background: #f5f5f7;
    border-bottom: 1px solid #d2d2d7;
    padding: 6px 12px;
    spacing: 8px;
}

QToolBar QLabel {
    font-size: 13px;
    font-weight: 500;
    color: #1d1d1f;
}

/* Buttons */
QPushButton {
    background-color: #007aff;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #0066d6;
}

QPushButton:pressed {
    background-color: #004ea2;
}

QPushButton:disabled {
    background-color: #c7c7cc;
    color: #8e8e93;
}

QPushButton#secondaryBtn {
    background-color: #e5e5ea;
    color: #1d1d1f;
}

QPushButton#secondaryBtn:hover {
    background-color: #d1d1d6;
}

QPushButton#dangerBtn {
    background-color: #ff3b30;
}

QPushButton#dangerBtn:hover {
    background-color: #d63029;
}

/* Toggle button (for auto-print) */
QPushButton#toggleBtn {
    background-color: #e5e5ea;
    color: #1d1d1f;
    border-radius: 14px;
    padding: 4px 16px;
    min-height: 28px;
}

QPushButton#toggleBtn:checked {
    background-color: #34c759;
    color: white;
}

/* List widget */
QListWidget {
    background-color: white;
    border: 1px solid #d2d2d7;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    border: none;
    border-bottom: 1px solid #f2f2f7;
    padding: 8px 4px;
    border-radius: 0px;
}

QListWidget::item:selected {
    background-color: #e8f0fe;
    color: #1d1d1f;
}

QListWidget::item:hover {
    background-color: #f5f5f7;
}

/* Scroll bars */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #c7c7cc;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Status bar */
QStatusBar {
    background: #f5f5f7;
    border-top: 1px solid #d2d2d7;
    font-size: 12px;
    color: #8e8e93;
    padding: 2px 8px;
}

/* Tab widget */
QTabWidget::pane {
    border: 1px solid #d2d2d7;
    border-radius: 8px;
    background: white;
    top: -1px;
}

QTabBar::tab {
    background: #e5e5ea;
    border: 1px solid #d2d2d7;
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
}

QTabBar::tab:selected {
    background: white;
    font-weight: 500;
}

QTabBar::tab:hover {
    background: #f0f0f5;
}

/* Text edit / code editor */
QPlainTextEdit {
    background: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 8px;
    font-family: "SF Mono", "Menlo", "Monaco", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #45475a;
}

/* Combo box */
QComboBox {
    background: white;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 28px;
}

QComboBox:hover {
    border-color: #007aff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

/* Spin box / Slider */
QSpinBox, QDoubleSpinBox {
    background: white;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 28px;
}

/* Line edit */
QLineEdit {
    background: white;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 28px;
}

QLineEdit:focus {
    border-color: #007aff;
}

/* Group box */
QGroupBox {
    font-weight: 600;
    border: 1px solid #d2d2d7;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #1d1d1f;
}

/* Labels */
QLabel#sectionTitle {
    font-size: 16px;
    font-weight: 600;
    color: #1d1d1f;
}

QLabel#subtitle {
    font-size: 12px;
    color: #8e8e93;
}

QLabel#statusLabel {
    font-size: 12px;
    color: #8e8e93;
}

/* Check box */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #c7c7cc;
}

QCheckBox::indicator:checked {
    background-color: #007aff;
    border-color: #007aff;
}

/* Splitter */
QSplitter::handle {
    background: #d2d2d7;
    height: 1px;
}
"""

# Compact task item widget style
TASK_ITEM_STYLE = """
QWidget#taskItem {
    background: transparent;
    padding: 4px;
}

QLabel#taskName {
    font-size: 14px;
    font-weight: 500;
    color: #1d1d1f;
}

QLabel#taskProject {
    font-size: 12px;
    color: #8e8e93;
}

QLabel#taskDueDate {
    font-size: 12px;
    color: #636366;
    font-weight: 500;
}

QLabel#taskTag {
    font-size: 10px;
    font-weight: 600;
    color: white;
    background: #1d1d1f;
    padding: 2px 6px;
    border-radius: 3px;
}
"""
