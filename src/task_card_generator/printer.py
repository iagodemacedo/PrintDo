"""Thermal printer functionality with macOS support."""

import platform
import logging

logger = logging.getLogger(__name__)


def print_to_thermal_printer(image_path, printer_config=None):
    """Print image to thermal printer.

    On macOS, uses the PrinterManager (USB/CUPS).
    On Windows, falls back to Win32Raw for backward compatibility.
    """
    system = platform.system()

    if system == "Darwin":
        # macOS - use PrinterManager
        from src.printing.printer_manager import PrinterManager

        manager = PrinterManager()
        printer = printer_config or manager.load_saved_printer()
        success = manager.print_image(image_path, printer)
        if success:
            logger.info("Successfully printed to thermal printer (macOS)")
        else:
            logger.error("Failed to print to thermal printer (macOS)")
        return success

    elif system == "Windows":
        # Windows - original Win32Raw approach
        try:
            from escpos.printer import Win32Raw

            printer = Win32Raw("RONGTA 80mm Series Printer")
            printer.image(image_path, impl="bitImageColumn", center=True)
            printer.cut()
            logger.info("Successfully printed to thermal printer (Windows)")
            return True
        except Exception as e:
            logger.error("ERROR printing to thermal printer: %s", e)
            return False

    else:
        # Linux / other - try CUPS
        from src.printing.printer_manager import PrinterManager

        manager = PrinterManager()
        return manager.print_image(image_path, printer_config)
