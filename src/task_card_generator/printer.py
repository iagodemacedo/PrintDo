"""Thermal printer functionality via CUPS on macOS."""

import subprocess
import tempfile
from typing import List


def list_printers() -> List[str]:
    """List available CUPS printers."""
    try:
        result = subprocess.run(
            ["lpstat", "-e"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return [
            line.strip()
            for line in result.stdout.strip().splitlines()
            if line.strip()
        ]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def print_to_thermal_printer(
    image_path: str,
    printer_name: str = None,
    top_margin: int = 0,
    bottom_margin: int = 0,
):
    """Print an image file to a CUPS thermal printer.

    Margins are implemented as ESC/POS paper feed commands so they
    work even when the driver trims blank image areas.

    Args:
        image_path: Path to the PNG image to print.
        printer_name: CUPS printer name. If None, uses system default.
        top_margin: Lines to feed before printing (≈ 1 line = ~4mm).
        bottom_margin: Lines to feed after printing, before cut.
    """
    # Feed paper for top margin
    if top_margin > 0:
        _send_raw(printer_name, b"\n" * top_margin)

    # Print the image
    cmd = ["lp"]
    if printer_name:
        cmd.extend(["-d", printer_name])

    cmd.extend([
        "-o", "orientation-requested=3",   # force portrait
        "-o", "TmxPaperCut=NoCut",         # we handle cut after bottom margin
        "-o", "TmxPaperReduction=Both",    # trim blank space from image
    ])
    cmd.append(image_path)

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Print failed: {result.stderr.strip()}")

    # Feed paper for bottom margin, then cut
    feed = b"\n" * max(bottom_margin, 1)
    cut = b"\x1d\x56\x00"  # ESC/POS GS V full cut
    _send_raw(printer_name, feed + cut)


def _send_raw(printer_name: str, data: bytes):
    """Send raw bytes to the printer via CUPS."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(data)
            path = f.name
        cmd = ["lp", "-o", "raw"]
        if printer_name:
            cmd.extend(["-d", printer_name])
        cmd.append(path)
        subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception:
        pass
