"""Menu bar application using rumps."""

import threading

import rumps

from ..task_card_generator.html_generator import create_task_image_from_html
from ..task_card_generator.print_log import PrintLog
from ..task_card_generator.printer import print_to_thermal_printer
from ..task_card_generator.template_engine import TemplateEngine
from ..task_card_generator.things3_service import Things3Service


class PrintDoApp(rumps.App):
    def __init__(self):
        super().__init__("PrintDo", quit_button="Quit")

        self.things3 = Things3Service()
        self.print_log = PrintLog()
        self.template_engine = TemplateEngine()
        self.polling = False
        self._poll_timer = None
        self._window_refs = []

        self.printer_name = self.print_log.get_setting("printer_name")
        self.poll_interval = int(
            self.print_log.get_setting("poll_interval", "60")
        )

        self.auto_print_item = rumps.MenuItem(
            "Auto-Print: OFF", callback=self.toggle_auto_print
        )

        self.menu = [
            rumps.MenuItem("Open PrintDo", callback=self.open_main_window),
            None,
            rumps.MenuItem("Print All Today", callback=self.print_all_today),
            self.auto_print_item,
            None,
            rumps.MenuItem("Edit Template...", callback=self.open_template_editor),
            rumps.MenuItem("Settings...", callback=self.open_settings),
        ]

    def open_main_window(self, _):
        from .main_window import open_main_window

        controller = open_main_window(
            self.things3, self.template_engine, self.print_log, self.printer_name
        )
        self._window_refs.append(controller)

    def print_all_today(self, _):
        threading.Thread(target=self._do_print_all, daemon=True).start()

    def _do_print_all(self):
        import time

        try:
            tasks = self.things3.get_today_tasks()
            if not tasks:
                rumps.notification("PrintDo", "", "No tasks in Today.")
                return
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
                        if count < len(tasks):
                            time.sleep(2)
                except Exception as e:
                    errors.append(str(e)[:60])
            msg = f"Printed {count}/{len(tasks)}." if errors else f"Printed {count} tasks."
            rumps.notification("PrintDo", "", msg)
        except Exception as e:
            rumps.notification("PrintDo", "Error", str(e)[:100])

    def toggle_auto_print(self, sender):
        self.polling = not self.polling
        sender.title = f"Auto-Print: {'ON' if self.polling else 'OFF'}"
        if self.polling:
            self._start_polling()
        elif self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

    def _start_polling(self):
        if self._poll_timer:
            self._poll_timer.stop()

        @rumps.timer(self.poll_interval)
        def poll(timer):
            if not self.polling:
                timer.stop()
                return
            self._poll_once()

        self._poll_timer = poll

    def _poll_once(self):
        try:
            tasks = self.things3.get_today_tasks()
            printed_count = 0
            width = self.template_engine.get_render_width()
            scale = self.template_engine.get_print_scale()
            top_m, bot_m = self.template_engine.get_margins()
            for task in tasks:
                if not self.print_log.is_printed(task.id):
                    html = self.template_engine.render(task)
                    image_path = create_task_image_from_html(html, width=width, scale=scale)
                    if image_path:
                        print_to_thermal_printer(
                            image_path, self.printer_name,
                            top_margin=top_m, bottom_margin=bot_m,
                        )
                        self.print_log.mark_printed(task.id, task.name)
                        printed_count += 1
            if printed_count:
                rumps.notification(
                    "PrintDo", "", f"Auto-printed {printed_count} new tasks."
                )
        except Exception:
            pass

    def open_template_editor(self, _):
        from .template_editor import open_template_editor

        controller = open_template_editor()
        self._window_refs.append(controller)

    def open_settings(self, _):
        from .settings_window import open_settings_window

        controller = open_settings_window(self)
        self._window_refs.append(controller)
