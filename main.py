#!/usr/bin/env python3
"""PrintDo - Print your Things 3 tasks on a thermal printer."""

import os

import AppKit

from src.gui.menu_bar import PrintDoApp


def main():
    from src.task_card_generator.config import CUSTOM_TEMPLATES_DIR

    custom_template = os.path.join(CUSTOM_TEMPLATES_DIR, "custom.html")
    if os.path.isfile(custom_template):
        os.environ["PRINTDO_TEMPLATE"] = custom_template

    # Create NSApplication and hide Dock icon before rumps takes over
    AppKit.NSApplication.sharedApplication()
    AppKit.NSApp.setActivationPolicy_(
        AppKit.NSApplicationActivationPolicyAccessory
    )

    app = PrintDoApp()
    app.run()


if __name__ == "__main__":
    main()
