# PrintDo

A macOS menu bar app that prints your [Things 3](https://culturedcode.com/things/) tasks on a thermal receipt printer.

![macOS](https://img.shields.io/badge/macOS-13%2B-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## How it works

PrintDo reads your Today tasks from Things 3 via AppleScript, renders them as styled cards using WebKit, and prints them on an Epson TM-T20X II (or compatible 80mm thermal printer) via CUPS.

It runs entirely offline — no API keys, no cloud services, no accounts.

## Features

- **Menu bar app** — lives in the macOS menu bar, no Dock icon
- **Task list window** — select and print individual tasks or all at once
- **Auto-print** — polls Things 3 for new tasks and prints them automatically
- **Drag-and-drop template editor** — reorder blocks (title, project, due date, tags, notes, separators), toggle visibility, adjust font sizes, margins, render width, and print quality
- **High-resolution output** — renders at configurable scale (1x–3x) with DPI metadata for sharp prints at 203 DPI
- **Print log** — tracks printed tasks (SQLite) to avoid duplicates during auto-print

## Requirements

- macOS 13+
- Python 3.12
- [Things 3](https://culturedcode.com/things/)
- 80mm thermal printer (tested with Epson TM-T20X II) configured in CUPS

## Installation

```bash
git clone https://github.com/iagodemacedo/PrintDo.git
cd PrintDo

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Run from source

```bash
source venv/bin/activate
python main.py
```

### Build standalone .app

```bash
source venv/bin/activate
pip install pyinstaller
pyinstaller PrintDo.spec

# The app is at dist/PrintDo.app
cp -R dist/PrintDo.app /Applications/
```

### Menu bar options

| Menu item | Description |
|---|---|
| **Open PrintDo** | Task list — select tasks, preview, and print |
| **Print All Today** | Print all Today tasks at once |
| **Auto-Print** | Toggle polling for new tasks |
| **Edit Template...** | Drag-and-drop block editor with live preview |
| **Settings...** | Configure printer name and poll interval |

## Printer setup

1. Connect your thermal printer via USB
2. Install the manufacturer's CUPS driver (Epson provides `.pkg` installers)
3. Verify with `lpstat -p` — you should see your printer listed
4. Set the printer name in PrintDo Settings (or leave blank for system default)

## Project structure

```
main.py                              # Entry point
src/
  gui/
    menu_bar.py                      # rumps menu bar app
    main_window.py                   # Task list window (Cocoa)
    template_editor.py               # Template editor window (WKWebView)
    editor_page.py                   # HTML/CSS/JS for drag-and-drop editor
    settings_window.py               # Settings window
  task_card_generator/
    things3_service.py               # Things 3 AppleScript integration
    template_engine.py               # Jinja2 template + block system
    webkit_renderer.py               # HTML to PNG via WKWebView
    html_generator.py                # Rendering wrapper with DPI metadata
    printer.py                       # CUPS printing + ESC/POS commands
    print_log.py                     # SQLite print history
    config.py                        # App paths and defaults
    templates/default.html           # Default card template
```

## Configuration files

Stored in `~/Library/Application Support/PrintDo/`:

| File | Description |
|---|---|
| `printdo.db` | Print log and settings (SQLite) |
| `templates/blocks.json` | Block order, toggles, and style settings |
| `templates/custom.html` | Generated Jinja2 template from block config |

## License

MIT License — see [LICENSE](LICENSE) for details.
