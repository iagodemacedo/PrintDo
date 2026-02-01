"""Main window for task selection and printing — native Cocoa."""

import threading

import AppKit
import Foundation
import objc

from ..task_card_generator.html_generator import create_task_image_from_html
from ..task_card_generator.print_log import PrintLog
from ..task_card_generator.printer import print_to_thermal_printer
from ..task_card_generator.template_engine import TemplateEngine
from ..task_card_generator.things3_service import Things3Service


class TaskRowView(AppKit.NSView):
    """A single task row with checkbox and labels."""

    def initWithTask_printed_(self, task, printed):
        frame = Foundation.NSMakeRect(0, 0, 440, 52)
        self = objc.super(TaskRowView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.task = task

        self.checkbox = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(8, 14, 24, 24)
        )
        self.checkbox.setButtonType_(AppKit.NSButtonTypeSwitch)
        self.checkbox.setTitle_("")
        self.checkbox.setState_(AppKit.NSControlStateValueOff)
        self.addSubview_(self.checkbox)

        title = AppKit.NSTextField.labelWithString_(task.name)
        title.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14, 0.5))
        title.setFrame_(Foundation.NSMakeRect(36, 27, 390, 20))
        self.addSubview_(title)

        parts = []
        if task.project:
            parts.append(task.project)
        if task.tags:
            parts.append(", ".join(task.tags))
        if task.due_date:
            parts.append(f"Due: {task.due_date}")
        if printed:
            parts.append("(printed)")

        subtitle_text = " | ".join(parts) if parts else ""
        subtitle = AppKit.NSTextField.labelWithString_(subtitle_text)
        subtitle.setFont_(AppKit.NSFont.systemFontOfSize_(11))
        subtitle.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        subtitle.setFrame_(Foundation.NSMakeRect(36, 7, 390, 16))
        self.addSubview_(subtitle)

        return self

    @objc.python_method
    def isChecked(self):
        return self.checkbox.state() == AppKit.NSControlStateValueOn

    def setChecked_(self, val):
        state = AppKit.NSControlStateValueOn if val else AppKit.NSControlStateValueOff
        self.checkbox.setState_(state)


class MainWindowController(AppKit.NSObject):
    """Controller for the main task list window."""

    def initWithServices_(self, services):
        self = objc.super(MainWindowController, self).init()
        if self is None:
            return None

        self.things3, self.template_engine, self.print_log, self.printer_name = services
        self.tasks = []
        self.task_rows = []
        self.previewWindows = []

        self._buildWindow()
        self._doRefresh()
        return self

    @objc.python_method
    def _buildWindow(self):
        style = (
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
            | AppKit.NSWindowStyleMaskResizable
            | AppKit.NSWindowStyleMaskMiniaturizable
        )
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            Foundation.NSMakeRect(200, 200, 480, 600),
            style,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("PrintDo")
        self.window.setMinSize_(Foundation.NSMakeSize(400, 400))
        self.window.center()

        content = self.window.contentView()

        title_label = AppKit.NSTextField.labelWithString_("Today's Tasks")
        title_label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(20))
        title_label.setFrame_(Foundation.NSMakeRect(16, 556, 200, 28))
        content.addSubview_(title_label)

        refresh_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(380, 558, 80, 28)
        )
        refresh_btn.setTitle_("Refresh")
        refresh_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        refresh_btn.setTarget_(self)
        refresh_btn.setAction_(objc.selector(self.refreshClicked_, signature=b"v@:@"))
        content.addSubview_(refresh_btn)

        self.scroll_view = AppKit.NSScrollView.alloc().initWithFrame_(
            Foundation.NSMakeRect(0, 60, 480, 490)
        )
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )
        self.scroll_view.setBorderType_(AppKit.NSNoBorder)

        self.list_view = AppKit.NSView.alloc().initWithFrame_(
            Foundation.NSMakeRect(0, 0, 480, 490)
        )
        self.scroll_view.setDocumentView_(self.list_view)
        content.addSubview_(self.scroll_view)

        # Status label
        self.statusLabel = AppKit.NSTextField.labelWithString_("")
        self.statusLabel.setFont_(AppKit.NSFont.systemFontOfSize_(11))
        self.statusLabel.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        self.statusLabel.setFrame_(Foundation.NSMakeRect(16, 44, 440, 16))
        content.addSubview_(self.statusLabel)

        # Bottom bar
        bottom = AppKit.NSView.alloc().initWithFrame_(
            Foundation.NSMakeRect(0, 0, 480, 44)
        )

        select_all_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(16, 10, 90, 28)
        )
        select_all_btn.setTitle_("Select All")
        select_all_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        select_all_btn.setTarget_(self)
        select_all_btn.setAction_(objc.selector(self.selectAllClicked_, signature=b"v@:@"))
        bottom.addSubview_(select_all_btn)

        deselect_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(112, 10, 100, 28)
        )
        deselect_btn.setTitle_("Deselect All")
        deselect_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        deselect_btn.setTarget_(self)
        deselect_btn.setAction_(objc.selector(self.deselectAllClicked_, signature=b"v@:@"))
        bottom.addSubview_(deselect_btn)

        preview_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(290, 10, 72, 28)
        )
        preview_btn.setTitle_("Preview")
        preview_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        preview_btn.setTarget_(self)
        preview_btn.setAction_(objc.selector(self.previewClicked_, signature=b"v@:@"))
        bottom.addSubview_(preview_btn)

        print_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(368, 10, 96, 28)
        )
        print_btn.setTitle_("Print Selected")
        print_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        print_btn.setKeyEquivalent_("\r")
        print_btn.setTarget_(self)
        print_btn.setAction_(objc.selector(self.printClicked_, signature=b"v@:@"))
        bottom.addSubview_(print_btn)

        content.addSubview_(bottom)

    # --- ObjC action selectors (one argument: sender) ---

    def refreshClicked_(self, sender):
        self._doRefresh()

    def selectAllClicked_(self, sender):
        for row in self.task_rows:
            row.setChecked_(True)

    def deselectAllClicked_(self, sender):
        for row in self.task_rows:
            row.setChecked_(False)

    def printClicked_(self, sender):
        selected = self._getSelectedTasks()
        if not selected:
            self.statusLabel.setStringValue_("No tasks selected.")
            return
        self.statusLabel.setStringValue_(f"Printing {len(selected)} tasks...")
        threading.Thread(
            target=self._doPrint, args=(selected,), daemon=True
        ).start()

    def previewClicked_(self, sender):
        selected = self._getSelectedTasks()
        if not selected:
            self.statusLabel.setStringValue_("Select a task to preview.")
            return
        self.statusLabel.setStringValue_("Rendering preview...")
        threading.Thread(
            target=self._doPreview, args=(selected[0],), daemon=True
        ).start()

    def setStatusText_(self, text):
        self.statusLabel.setStringValue_(text or "")

    def showPreviewImage_(self, image_path):
        image = AppKit.NSImage.alloc().initWithContentsOfFile_(image_path)
        if image is None:
            return

        size = image.size()
        style = (
            AppKit.NSWindowStyleMaskTitled | AppKit.NSWindowStyleMaskClosable
        )
        preview_win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            Foundation.NSMakeRect(300, 200, size.width + 32, size.height + 32),
            style,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        preview_win.setTitle_("Print Preview")
        preview_win.center()

        img_view = AppKit.NSImageView.alloc().initWithFrame_(
            Foundation.NSMakeRect(16, 16, size.width, size.height)
        )
        img_view.setImage_(image)
        img_view.setImageScaling_(AppKit.NSImageScaleProportionallyUpOrDown)
        preview_win.contentView().addSubview_(img_view)

        preview_win.makeKeyAndOrderFront_(None)
        self.previewWindows.append(preview_win)
        self.statusLabel.setStringValue_("Preview ready.")

    # --- Python-only methods (not ObjC selectors) ---

    @objc.python_method
    def _doRefresh(self):
        for row in self.task_rows:
            row.removeFromSuperview()
        self.task_rows.clear()

        try:
            self.tasks = self.things3.get_today_tasks()
        except RuntimeError as e:
            self.statusLabel.setStringValue_(f"Error: {e}")
            return

        if not self.tasks:
            self.statusLabel.setStringValue_("No tasks in Today.")
            self.list_view.setFrameSize_(Foundation.NSMakeSize(480, 490))
            return

        printed_ids = self.print_log.get_printed_ids()
        total_height = len(self.tasks) * 52
        self.list_view.setFrameSize_(
            Foundation.NSMakeSize(480, max(total_height, 490))
        )

        for i, task in enumerate(self.tasks):
            y = total_height - (i + 1) * 52
            row = TaskRowView.alloc().initWithTask_printed_(
                task, task.id in printed_ids
            )
            row.setFrame_(Foundation.NSMakeRect(0, y, 460, 52))
            self.list_view.addSubview_(row)
            self.task_rows.append(row)

        self.statusLabel.setStringValue_(f"{len(self.tasks)} tasks loaded")

    @objc.python_method
    def _getSelectedTasks(self):
        return [row.task for row in self.task_rows if row.isChecked()]

    @objc.python_method
    def _doPrint(self, tasks):
        import time

        count = 0
        errors = []
        width = self.template_engine.get_render_width()
        scale = self.template_engine.get_print_scale()
        top_m, bot_m = self.template_engine.get_margins()
        for task in tasks:
            try:
                html = self.template_engine.render(task)
                image_path = create_task_image_from_html(html, width=width, scale=scale)
                if image_path:
                    print_to_thermal_printer(
                        image_path, self.printer_name,
                        top_margin=top_m, bottom_margin=bot_m,
                    )
                    self.print_log.mark_printed(task.id, task.name)
                    count += 1
                    # Give the printer time to process before next job
                    if count < len(tasks):
                        time.sleep(2)
            except Exception as e:
                errors.append(f"{task.name}: {e}")

        if errors:
            msg = f"Printed {count}/{len(tasks)}. Errors: {'; '.join(errors)}"
        else:
            msg = f"Printed {count} tasks."

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setStatusText:", msg, False
        )
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "refreshClicked:", None, False
        )

    @objc.python_method
    def _doPreview(self, task):
        try:
            width = self.template_engine.get_render_width()
            scale = self.template_engine.get_print_scale()
            html = self.template_engine.render(task)
            image_path = create_task_image_from_html(html, width=width, scale=scale)
            if image_path:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "showPreviewImage:", image_path, False
                )
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "setStatusText:", f"Preview error: {e}", False
            )

    @objc.python_method
    def show(self):
        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)


def open_main_window(things3, template_engine, print_log, printer_name):
    """Open the main window. Must be called on the main thread."""
    controller = MainWindowController.alloc().initWithServices_(
        (things3, template_engine, print_log, printer_name)
    )
    controller.show()
    return controller
