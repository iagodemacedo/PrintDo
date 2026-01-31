"""PrintDo application setup."""

import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.gui.styles import MAIN_STYLESHEET

logger = logging.getLogger(__name__)


class PrintDoApp(QApplication):
    """Main application class with macOS configuration."""

    def __init__(self, argv):
        super().__init__(argv)

        self.setApplicationName("PrintDo")
        self.setOrganizationName("PrintDo")
        self.setOrganizationDomain("com.printdo.app")

        # Apply stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)

        # macOS specific
        self.setQuitOnLastWindowClosed(True)
