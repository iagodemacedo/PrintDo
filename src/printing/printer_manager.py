"""macOS printer abstraction supporting USB thermal printers and CUPS."""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class PrinterType(Enum):
    USB = "usb"
    NETWORK = "network"
    CUPS = "cups"


@dataclass
class PrinterInfo:
    """Information about a discovered printer."""

    name: str = ""
    printer_type: PrinterType = PrinterType.CUPS
    # USB identifiers
    vendor_id: int = 0
    product_id: int = 0
    # Network identifiers
    host: str = ""
    port: int = 9100
    # CUPS name
    cups_name: str = ""

    def display_name(self) -> str:
        if self.name:
            return self.name
        if self.printer_type == PrinterType.USB:
            return f"USB Printer ({self.vendor_id:04x}:{self.product_id:04x})"
        if self.printer_type == PrinterType.NETWORK:
            return f"Network Printer ({self.host}:{self.port})"
        return self.cups_name or "Unknown Printer"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "printer_type": self.printer_type.value,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "host": self.host,
            "port": self.port,
            "cups_name": self.cups_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PrinterInfo":
        return cls(
            name=data.get("name", ""),
            printer_type=PrinterType(data.get("printer_type", "cups")),
            vendor_id=data.get("vendor_id", 0),
            product_id=data.get("product_id", 0),
            host=data.get("host", ""),
            port=data.get("port", 9100),
            cups_name=data.get("cups_name", ""),
        )


class PrinterManager:
    """Manages printer discovery and printing on macOS."""

    def __init__(self):
        self._config_dir = Path.home() / "Library" / "Application Support" / "PrintDo"
        self._config_file = self._config_dir / "printer_config.json"

    def discover_usb_printers(self) -> List[PrinterInfo]:
        """Discover USB thermal printers via pyusb."""
        printers = []
        try:
            import usb.core
            import usb.util

            # Common thermal printer vendor IDs
            thermal_vendors = {
                0x0416: "Winbond",
                0x0483: "STMicroelectronics",
                0x04B8: "Epson",
                0x0519: "Star Micronics",
                0x0525: "Netchip",
                0x067B: "Prolific",
                0x0FE6: "ICS",
                0x1504: "RONGTA",
                0x1A86: "QinHeng",
                0x1CB0: "Custom",
                0x20D1: "Dinglicom",
                0x28E9: "GD",
                0x4348: "WCH",
            }

            devices = usb.core.find(find_all=True)
            if devices:
                for device in devices:
                    vid = device.idVendor
                    if vid in thermal_vendors:
                        name = thermal_vendors.get(vid, "Unknown")
                        try:
                            product = usb.util.get_string(device, device.iProduct) or ""
                            if product:
                                name = product
                        except Exception:
                            pass
                        printers.append(
                            PrinterInfo(
                                name=name,
                                printer_type=PrinterType.USB,
                                vendor_id=vid,
                                product_id=device.idProduct,
                            )
                        )
        except ImportError:
            logger.info("pyusb not installed - USB discovery unavailable")
        except Exception as e:
            logger.warning("USB discovery failed: %s", e)

        return printers

    def discover_cups_printers(self) -> List[PrinterInfo]:
        """Discover printers known to CUPS on macOS."""
        printers = []
        try:
            result = subprocess.run(
                ["lpstat", "-p"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    # Format: "printer NAME is idle." or "printer NAME disabled ..."
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == "printer":
                        cups_name = parts[1]
                        printers.append(
                            PrinterInfo(
                                name=cups_name,
                                printer_type=PrinterType.CUPS,
                                cups_name=cups_name,
                            )
                        )
        except Exception as e:
            logger.warning("CUPS discovery failed: %s", e)

        return printers

    def discover_all_printers(self) -> List[PrinterInfo]:
        """Discover all available printers."""
        printers = []
        printers.extend(self.discover_usb_printers())
        printers.extend(self.discover_cups_printers())
        return printers

    def print_image(self, image_path: str, printer: Optional[PrinterInfo] = None) -> bool:
        """Print an image to the specified printer."""
        if printer is None:
            printer = self.load_saved_printer()

        if printer is None:
            # Try CUPS default
            return self._print_via_cups_default(image_path)

        if printer.printer_type == PrinterType.USB:
            return self._print_via_usb(image_path, printer)
        elif printer.printer_type == PrinterType.NETWORK:
            return self._print_via_network(image_path, printer)
        else:
            return self._print_via_cups(image_path, printer)

    def _print_via_usb(self, image_path: str, printer: PrinterInfo) -> bool:
        """Print using python-escpos USB backend."""
        try:
            from escpos.printer import Usb

            p = Usb(printer.vendor_id, printer.product_id)
            p.image(image_path, impl="bitImageColumn", center=True)
            p.cut()
            logger.info("Printed via USB: %s", printer.display_name())
            return True
        except ImportError:
            logger.error("python-escpos not installed")
            return False
        except Exception as e:
            logger.error("USB print failed: %s", e)
            # Fallback to CUPS if USB fails
            logger.info("Falling back to CUPS...")
            return self._print_via_cups_default(image_path)

    def _print_via_network(self, image_path: str, printer: PrinterInfo) -> bool:
        """Print using python-escpos Network backend."""
        try:
            from escpos.printer import Network

            p = Network(printer.host, port=printer.port)
            p.image(image_path, impl="bitImageColumn", center=True)
            p.cut()
            logger.info("Printed via Network: %s", printer.display_name())
            return True
        except ImportError:
            logger.error("python-escpos not installed")
            return False
        except Exception as e:
            logger.error("Network print failed: %s", e)
            return False

    def _print_via_cups(self, image_path: str, printer: PrinterInfo) -> bool:
        """Print using CUPS lp command."""
        try:
            result = subprocess.run(
                ["lp", "-d", printer.cups_name, image_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Printed via CUPS: %s", printer.cups_name)
                return True
            else:
                logger.error("CUPS print failed: %s", result.stderr)
                return False
        except Exception as e:
            logger.error("CUPS print failed: %s", e)
            return False

    def _print_via_cups_default(self, image_path: str) -> bool:
        """Print to the default CUPS printer."""
        try:
            result = subprocess.run(
                ["lp", image_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Printed via default CUPS printer")
                return True
            else:
                logger.error("Default CUPS print failed: %s", result.stderr)
                return False
        except Exception as e:
            logger.error("Default CUPS print failed: %s", e)
            return False

    def save_printer(self, printer: PrinterInfo) -> None:
        """Save selected printer to config."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w") as f:
            json.dump(printer.to_dict(), f, indent=2)

    def load_saved_printer(self) -> Optional[PrinterInfo]:
        """Load previously saved printer config."""
        if not self._config_file.exists():
            return None
        try:
            with open(self._config_file) as f:
                data = json.load(f)
            return PrinterInfo.from_dict(data)
        except Exception as e:
            logger.warning("Could not load printer config: %s", e)
            return None
