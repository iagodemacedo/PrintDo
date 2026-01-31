#!/usr/bin/env python3
"""PrintDo - Thermal printer task cards from Things 3.

Launch the GUI application, or use --cli for the original CLI mode.
"""

import sys
import logging
import argparse


def main():
    parser = argparse.ArgumentParser(description="PrintDo - Print task cards from Things 3")
    parser.add_argument("--cli", action="store_true", help="Run in original CLI mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.cli:
        # Original CLI mode
        from main_cli import main as cli_main
        cli_main()
        return

    # GUI mode
    from PySide6.QtWidgets import QApplication
    from src.gui.app import PrintDoApp
    from src.gui.main_window import MainWindow

    app = PrintDoApp(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()