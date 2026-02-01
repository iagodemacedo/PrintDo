"""HTML to image conversion for task cards.

Uses WebKit renderer (PyObjC) for converting HTML to PNG images.
Stamps DPI metadata so CUPS maps the image to the correct physical size.
"""

from PIL import Image

from .config import DEFAULT_PRINTER_WIDTH
from .webkit_renderer import html_to_image

_PRINTER_DPI = 203


def create_task_image_from_html(
    html_content: str,
    width: int = DEFAULT_PRINTER_WIDTH,
    scale: int = 2,
) -> str:
    """Convert an HTML string to a PNG image suitable for thermal printing.

    Args:
        html_content: Full HTML document string.
        width: CSS design width (default 576 for 72mm at 203 DPI).
        scale: Render multiplier for sharper output (2 = 1152px render).

    Returns:
        Path to the generated PNG file.
    """
    path = html_to_image(html_content, width, scale)

    # Set DPI so CUPS prints at the correct physical size.
    # e.g. scale=2 → 1152px at 406 DPI → 2.84 inches → 72mm
    target_dpi = _PRINTER_DPI * scale
    img = Image.open(path)
    img.save(path, dpi=(target_dpi, target_dpi))

    return path
