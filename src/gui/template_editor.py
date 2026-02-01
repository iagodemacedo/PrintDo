"""Template editor window — drag-and-drop block editor using WKWebView."""

import json
import os
import threading

import AppKit
import Foundation
import WebKit
import objc

from ..task_card_generator.config import CUSTOM_TEMPLATES_DIR
from ..task_card_generator.html_generator import create_task_image_from_html
from ..task_card_generator.template_engine import (
    TemplateEngine,
    generate_template_from_blocks,
    get_default_blocks_config,
)
from ..task_card_generator.things3_service import Things3Task
from .editor_page import EDITOR_HTML

SAMPLE_TASK = Things3Task(
    id="sample",
    name="Review Q1 Report",
    notes="Check revenue numbers and update projections for the board meeting.",
    due_date="February 15, 2025",
    tags=["work", "urgent"],
    project="Quarterly Review",
    status="open",
)


class _EditorNavDelegate(AppKit.NSObject):
    """Injects editor config into the WKWebView after the page loads."""

    def webView_didFinishNavigation_(self, webview, navigation):
        cfg = json.dumps(self._editor_config)
        webview.evaluateJavaScript_completionHandler_(
            f"initEditor({cfg});", None
        )


class TemplateEditorController(AppKit.NSObject):
    """Controller for the drag-and-drop template editor window."""

    def init(self):
        self = objc.super(TemplateEditorController, self).init()
        if self is None:
            return None
        self.engine = TemplateEngine()
        self._build_window()
        self._load_editor()
        return self

    @objc.python_method
    def _build_window(self):
        style = (
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
            | AppKit.NSWindowStyleMaskResizable
        )
        self.window = (
            AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                Foundation.NSMakeRect(100, 100, 860, 600),
                style,
                AppKit.NSBackingStoreBuffered,
                False,
            )
        )
        self.window.setTitle_("PrintDo - Template Editor")
        self.window.setMinSize_(Foundation.NSMakeSize(700, 450))
        self.window.center()

        content = self.window.contentView()

        # Header
        title = AppKit.NSTextField.labelWithString_("Template Editor")
        title.setFont_(AppKit.NSFont.boldSystemFontOfSize_(18))
        title.setFrame_(Foundation.NSMakeRect(16, 564, 200, 24))
        content.addSubview_(title)

        # Buttons
        for label, x, action in [
            ("Reset", 550, "resetClicked_"),
            ("Preview", 650, "previewClicked_"),
            ("Save", 750, "saveClicked_"),
        ]:
            btn = AppKit.NSButton.alloc().initWithFrame_(
                Foundation.NSMakeRect(x, 562, 90, 28)
            )
            btn.setTitle_(label)
            btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            btn.setTarget_(self)
            btn.setAction_(
                objc.selector(getattr(self, action), signature=b"v@:@")
            )
            if label == "Save":
                btn.setKeyEquivalent_("\r")
            content.addSubview_(btn)

        # Hint
        hint = AppKit.NSTextField.labelWithString_(
            "Drag blocks to reorder \u2022 Toggle to show/hide"
        )
        hint.setFont_(AppKit.NSFont.systemFontOfSize_(11))
        hint.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        hint.setFrame_(Foundation.NSMakeRect(16, 542, 500, 16))
        content.addSubview_(hint)

        # Editor WKWebView (left)
        wk_config = WebKit.WKWebViewConfiguration.alloc().init()
        self.editor_web = WebKit.WKWebView.alloc().initWithFrame_configuration_(
            Foundation.NSMakeRect(0, 30, 520, 508), wk_config
        )
        content.addSubview_(self.editor_web)

        # Preview pane (right)
        self.preview_scroll = AppKit.NSScrollView.alloc().initWithFrame_(
            Foundation.NSMakeRect(524, 30, 336, 508)
        )
        self.preview_scroll.setHasVerticalScroller_(True)
        self.preview_scroll.setBorderType_(AppKit.NSBezelBorder)
        self.preview_scroll.setBackgroundColor_(
            AppKit.NSColor.colorWithWhite_alpha_(0.96, 1.0)
        )
        self.preview_view = AppKit.NSView.alloc().initWithFrame_(
            Foundation.NSMakeRect(0, 0, 320, 508)
        )
        self.preview_scroll.setDocumentView_(self.preview_view)
        content.addSubview_(self.preview_scroll)

        # Status
        self.status_label = AppKit.NSTextField.labelWithString_("")
        self.status_label.setFont_(AppKit.NSFont.systemFontOfSize_(11))
        self.status_label.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        self.status_label.setFrame_(Foundation.NSMakeRect(16, 6, 600, 16))
        content.addSubview_(self.status_label)

    @objc.python_method
    def _load_editor(self):
        """Load the editor HTML page and inject the current config."""
        config = self.engine.load_blocks_config()

        self._nav_delegate = _EditorNavDelegate.alloc().init()
        self._nav_delegate._editor_config = config
        self.editor_web.setNavigationDelegate_(self._nav_delegate)
        self.editor_web.loadHTMLString_baseURL_(EDITOR_HTML, None)

    # ---- JS bridge helper ----

    @objc.python_method
    def _read_config(self, callback):
        """Read full config from the JS editor, then call *callback(config)*."""

        def handler(result, error):
            if error:
                self.status_label.setStringValue_(f"JS error: {error}")
                return
            try:
                config = json.loads(result)
                callback(config)
            except Exception as e:
                self.status_label.setStringValue_(f"Parse error: {e}")

        self.editor_web.evaluateJavaScript_completionHandler_(
            "getConfig()", handler
        )

    # ---- ObjC action selectors ----

    def previewClicked_(self, sender):
        self.status_label.setStringValue_("Rendering preview\u2026")
        self._read_config(self._start_preview)

    def saveClicked_(self, sender):
        self._read_config(self._do_save)

    def resetClicked_(self, sender):
        # Remove custom files
        for name in ("blocks.json", "custom.html"):
            path = os.path.join(CUSTOM_TEMPLATES_DIR, name)
            if os.path.exists(path):
                os.remove(path)

        # Re-inject defaults into editor
        cfg = json.dumps(get_default_blocks_config())
        self.editor_web.evaluateJavaScript_completionHandler_(
            f"initEditor({cfg});", None
        )
        self.status_label.setStringValue_("Reset to default template.")

    def setStatusText_(self, text):
        self.status_label.setStringValue_(text or "")

    def showPreviewImage_(self, image_path):
        for subview in self.preview_view.subviews():
            subview.removeFromSuperview()

        image = AppKit.NSImage.alloc().initWithContentsOfFile_(image_path)
        if image is None:
            return

        size = image.size()
        max_w = 300.0
        if size.width > max_w:
            ratio = max_w / size.width
            display_w = max_w
            display_h = size.height * ratio
        else:
            display_w = size.width
            display_h = size.height

        self.preview_view.setFrameSize_(
            Foundation.NSMakeSize(display_w + 16, display_h + 16)
        )

        img_view = AppKit.NSImageView.alloc().initWithFrame_(
            Foundation.NSMakeRect(8, 8, display_w, display_h)
        )
        img_view.setImage_(image)
        img_view.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
        self.preview_view.addSubview_(img_view)
        self.status_label.setStringValue_("Preview updated.")

    # ---- Python-only helpers ----

    @objc.python_method
    def _start_preview(self, blocks):
        threading.Thread(
            target=self._do_preview, args=(blocks,), daemon=True
        ).start()

    @objc.python_method
    def _do_preview(self, config):
        try:
            html_template = generate_template_from_blocks(config)
            rendered = self.engine.render_from_string(html_template, SAMPLE_TASK)
            s = config.get("style") or {}
            width = s.get("render_width", 576)
            scale = s.get("print_scale", 2)
            image_path = create_task_image_from_html(rendered, width=width, scale=scale)
            if image_path:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "showPreviewImage:", image_path, False
                )
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "setStatusText:", f"Error: {e}", False
            )

    @objc.python_method
    def _do_save(self, blocks):
        try:
            self.engine.save_blocks_config(blocks)
            self.status_label.setStringValue_("Template saved.")
        except Exception as e:
            self.status_label.setStringValue_(f"Save error: {e}")

    @objc.python_method
    def show(self):
        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)


def open_template_editor():
    """Open the template editor."""
    controller = TemplateEditorController.alloc().init()
    controller.show()
    return controller
