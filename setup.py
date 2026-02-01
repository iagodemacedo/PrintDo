"""py2app build configuration for PrintDo."""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("templates", ["src/task_card_generator/templates/default.html"]),
]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "PrintDo",
        "CFBundleDisplayName": "PrintDo",
        "CFBundleIdentifier": "com.printdo.app",
        "CFBundleVersion": "2.0.0",
        "CFBundleShortVersionString": "2.0.0",
        "LSUIElement": True,
        "NSAppleEventsUsageDescription": (
            "PrintDo needs AppleScript access to read your Things 3 tasks."
        ),
    },
    "packages": [
        "rumps",
        "jinja2",
        "PIL",
    ],
    "excludes": [
        "packaging",
        "setuptools",
        "py2app",
        "test",
    ],
    "includes": [
        "src",
        "src.gui",
        "src.gui.editor_page",
        "src.gui.main_window",
        "src.gui.menu_bar",
        "src.gui.template_editor",
        "src.gui.settings_window",
        "src.task_card_generator",
        "src.task_card_generator.config",
        "src.task_card_generator.html_generator",
        "src.task_card_generator.print_log",
        "src.task_card_generator.printer",
        "src.task_card_generator.template_engine",
        "src.task_card_generator.things3_service",
        "src.task_card_generator.webkit_renderer",
        "objc",
        "AppKit",
        "Foundation",
        "WebKit",
    ],
}

setup(
    name="PrintDo",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
