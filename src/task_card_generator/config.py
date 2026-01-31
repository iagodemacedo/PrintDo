"""Configuration and imports for the task card generator."""

# PIL imports
try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not installed. Task card images will not be generated.")

# ReportLab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF functionality will be limited.")

# pdf2image imports
try:
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not installed. PDF to image conversion will not work.")

# Platform-aware font paths
import platform

if platform.system() == "Darwin":
    SYSTEM_FONT_PATHS = [
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    EMOJI_FONT_PATHS = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",
    ]
else:
    SYSTEM_FONT_PATHS = [
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf",
    ]
    EMOJI_FONT_PATHS = [
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/segoeuiemoji.ttf",
        "C:/Windows/Fonts/seguisym.ttf",
    ]

# OpenAI and printer imports
