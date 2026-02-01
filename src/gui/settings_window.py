"""Settings window — native Cocoa."""

import AppKit
import Foundation
import objc

from ..task_card_generator.printer import list_printers


class SettingsWindowController(AppKit.NSObject):
    """Controller for the settings window."""

    def initWithAppRef_(self, app_ref):
        self = objc.super(SettingsWindowController, self).init()
        if self is None:
            return None
        self.app_ref = app_ref
        self.print_log = app_ref.print_log
        self._build_window()
        return self

    @objc.python_method
    def _build_window(self):
        style = (
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
        )
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            Foundation.NSMakeRect(300, 300, 400, 320),
            style,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("PrintDo Settings")
        self.window.center()

        content = self.window.contentView()
        y = 260

        # Title
        title = AppKit.NSTextField.labelWithString_("Settings")
        title.setFont_(AppKit.NSFont.boldSystemFontOfSize_(20))
        title.setFrame_(Foundation.NSMakeRect(20, y, 200, 28))
        content.addSubview_(title)

        # Printer
        y -= 40
        printer_label = AppKit.NSTextField.labelWithString_("Printer:")
        printer_label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(13))
        printer_label.setFrame_(Foundation.NSMakeRect(20, y, 100, 20))
        content.addSubview_(printer_label)

        y -= 28
        printers = list_printers()
        current_printer = self.print_log.get_setting("printer_name", "")
        if not printers:
            printers = ["(no printers found)"]

        self.printer_popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
            Foundation.NSMakeRect(20, y, 360, 26), False
        )
        self.printer_popup.addItemsWithTitles_(printers)
        if current_printer in printers:
            self.printer_popup.selectItemWithTitle_(current_printer)
        content.addSubview_(self.printer_popup)

        # Poll interval
        y -= 40
        interval_label = AppKit.NSTextField.labelWithString_(
            "Auto-Print Poll Interval (seconds):"
        )
        interval_label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(13))
        interval_label.setFrame_(Foundation.NSMakeRect(20, y, 300, 20))
        content.addSubview_(interval_label)

        y -= 30
        current_interval = int(self.print_log.get_setting("poll_interval", "60"))

        self.interval_slider = AppKit.NSSlider.alloc().initWithFrame_(
            Foundation.NSMakeRect(20, y, 300, 24)
        )
        self.interval_slider.setMinValue_(15)
        self.interval_slider.setMaxValue_(300)
        self.interval_slider.setIntegerValue_(current_interval)
        self.interval_slider.setTarget_(self)
        self.interval_slider.setAction_(
            objc.selector(self.sliderChanged_, signature=b"v@:@")
        )
        content.addSubview_(self.interval_slider)

        self.interval_value_label = AppKit.NSTextField.labelWithString_(
            f"{current_interval}s"
        )
        self.interval_value_label.setFrame_(Foundation.NSMakeRect(330, y, 50, 20))
        content.addSubview_(self.interval_value_label)

        # Clear history
        y -= 44
        history_label = AppKit.NSTextField.labelWithString_("Print History:")
        history_label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(13))
        history_label.setFrame_(Foundation.NSMakeRect(20, y, 200, 20))
        content.addSubview_(history_label)

        y -= 30
        clear_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(20, y, 180, 28)
        )
        clear_btn.setTitle_("Clear Print History")
        clear_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        clear_btn.setTarget_(self)
        clear_btn.setAction_(
            objc.selector(self.clearHistoryClicked_, signature=b"v@:@")
        )
        content.addSubview_(clear_btn)

        self.history_status = AppKit.NSTextField.labelWithString_("")
        self.history_status.setFont_(AppKit.NSFont.systemFontOfSize_(11))
        self.history_status.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        self.history_status.setFrame_(Foundation.NSMakeRect(210, y + 4, 170, 16))
        content.addSubview_(self.history_status)

        # Save button
        y -= 44
        save_btn = AppKit.NSButton.alloc().initWithFrame_(
            Foundation.NSMakeRect(290, y, 90, 32)
        )
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        save_btn.setKeyEquivalent_("\r")
        save_btn.setTarget_(self)
        save_btn.setAction_(
            objc.selector(self.saveClicked_, signature=b"v@:@")
        )
        content.addSubview_(save_btn)

    def sliderChanged_(self, sender):
        val = int(sender.integerValue())
        self.interval_value_label.setStringValue_(f"{val}s")

    def clearHistoryClicked_(self, sender):
        self.print_log.clear_history()
        self.history_status.setStringValue_("Cleared.")

    def saveClicked_(self, sender):
        printer = self.printer_popup.titleOfSelectedItem()
        interval = int(self.interval_slider.integerValue())

        self.print_log.set_setting("printer_name", printer)
        self.print_log.set_setting("poll_interval", str(interval))

        self.app_ref.printer_name = printer
        self.app_ref.poll_interval = interval

        self.window.close()

    @objc.python_method
    def show(self):
        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)


def open_settings_window(app_ref):
    """Open the settings window."""
    controller = SettingsWindowController.alloc().initWithAppRef_(app_ref)
    controller.show()
    return controller
