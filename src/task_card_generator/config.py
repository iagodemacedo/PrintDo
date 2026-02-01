"""Configuration for PrintDo."""

import os

# App paths
APP_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/PrintDo")
CUSTOM_TEMPLATES_DIR = os.path.join(APP_SUPPORT_DIR, "templates")

# Defaults
DEFAULT_POLL_INTERVAL = 60  # seconds
DEFAULT_PRINTER_WIDTH = 576  # pixels (72mm thermal printer at 203 DPI)

# Ensure directories exist
os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
os.makedirs(CUSTOM_TEMPLATES_DIR, exist_ok=True)
