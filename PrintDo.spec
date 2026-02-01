# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PrintDo."""

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("src/task_card_generator/templates/default.html", "src/task_card_generator/templates"),
    ],
    hiddenimports=[
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
        "rumps",
        "jinja2",
        "PIL",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PrintDo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PrintDo",
)

app = BUNDLE(
    coll,
    name="PrintDo.app",
    bundle_identifier="com.printdo.app",
    info_plist={
        "CFBundleName": "PrintDo",
        "CFBundleDisplayName": "PrintDo",
        "CFBundleVersion": "2.0.0",
        "CFBundleShortVersionString": "2.0.0",
        "LSUIElement": True,
        "NSAppleEventsUsageDescription": (
            "PrintDo needs AppleScript access to read your Things 3 tasks."
        ),
    },
)
