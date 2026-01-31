"""py2app build configuration for PrintDo.

Build a macOS .app bundle:
    python setup.py py2app

Development mode (alias):
    python setup.py py2app -A
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("resources/templates", [
        "resources/templates/default.html.j2",
        "resources/templates/minimal.html.j2",
        "resources/templates/detailed.html.j2",
    ]),
]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "PrintDo",
        "CFBundleDisplayName": "PrintDo",
        "CFBundleIdentifier": "com.printdo.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "12.0",
        "NSAppleEventsUsageDescription": (
            "PrintDo needs access to Things 3 to read your tasks."
        ),
        "NSHumanReadableCopyright": "Copyright 2025 PrintDo",
    },
    "packages": [
        "PySide6",
        "jinja2",
        "src",
    ],
    "includes": [
        "src.things3",
        "src.gui",
        "src.printing",
        "src.database",
        "src.task_card_generator",
    ],
    "excludes": [
        "tkinter",
        "matplotlib",
        "scipy",
        "numpy",
        "selenium",
        "imgkit",
    ],
}

setup(
    name="PrintDo",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
