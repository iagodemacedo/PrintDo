"""Printer discovery and configuration widget."""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.printing.printer_manager import PrinterInfo, PrinterManager, PrinterType

logger = logging.getLogger(__name__)


class PrinterSettingsWidget(QWidget):
    """Widget for configuring the thermal printer."""

    printer_changed = Signal(object)  # PrinterInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = PrinterManager()
        self._printers: list = []
        self._build_ui()
        self._refresh_printers()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Discovered printers
        discovered_group = QGroupBox("Detected Printers")
        dg_layout = QVBoxLayout(discovered_group)

        printer_row = QHBoxLayout()
        self._printer_combo = QComboBox()
        self._printer_combo.setMinimumWidth(250)
        self._printer_combo.currentIndexChanged.connect(self._on_printer_selected)
        printer_row.addWidget(self._printer_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._refresh_printers)
        printer_row.addWidget(refresh_btn)

        dg_layout.addLayout(printer_row)
        layout.addWidget(discovered_group)

        # Manual network printer
        network_group = QGroupBox("Network Printer (Manual)")
        ng_layout = QVBoxLayout(network_group)

        host_row = QHBoxLayout()
        host_row.addWidget(QLabel("Host:"))
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("192.168.1.100")
        host_row.addWidget(self._host_input)

        host_row.addWidget(QLabel("Port:"))
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(9100)
        host_row.addWidget(self._port_input)

        ng_layout.addLayout(host_row)

        add_net_btn = QPushButton("Add Network Printer")
        add_net_btn.setObjectName("secondaryBtn")
        add_net_btn.clicked.connect(self._add_network_printer)
        ng_layout.addWidget(add_net_btn)

        layout.addWidget(network_group)
        layout.addStretch()

    def _refresh_printers(self):
        self._printers = self._manager.discover_all_printers()
        self._printer_combo.blockSignals(True)
        self._printer_combo.clear()

        if not self._printers:
            self._printer_combo.addItem("No printers found")
        else:
            for p in self._printers:
                self._printer_combo.addItem(p.display_name())

            # Try to select saved printer
            saved = self._manager.load_saved_printer()
            if saved:
                for i, p in enumerate(self._printers):
                    if p.cups_name == saved.cups_name or (
                        p.vendor_id == saved.vendor_id and p.product_id == saved.product_id
                    ):
                        self._printer_combo.setCurrentIndex(i)
                        break

        self._printer_combo.blockSignals(False)

    def _on_printer_selected(self, index: int):
        if 0 <= index < len(self._printers):
            printer = self._printers[index]
            self._manager.save_printer(printer)
            self.printer_changed.emit(printer)

    def _add_network_printer(self):
        host = self._host_input.text().strip()
        if not host:
            return
        port = self._port_input.value()
        printer = PrinterInfo(
            name=f"Network ({host}:{port})",
            printer_type=PrinterType.NETWORK,
            host=host,
            port=port,
        )
        self._printers.append(printer)
        self._printer_combo.addItem(printer.display_name())
        self._printer_combo.setCurrentIndex(len(self._printers) - 1)

    def get_selected_printer(self) -> PrinterInfo:
        idx = self._printer_combo.currentIndex()
        if 0 <= idx < len(self._printers):
            return self._printers[idx]
        return None
