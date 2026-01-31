"""Background poller that watches Things 3 Today list for new tasks."""

import logging
from typing import Set

from PySide6.QtCore import QThread, Signal

from .bridge import Things3Bridge
from .models import Things3Task

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_MS = 30_000  # 30 seconds


class Things3Poller(QThread):
    """Polls Things 3 Today list and emits signals when new tasks appear."""

    new_tasks_found = Signal(list)  # List[Things3Task]
    poll_error = Signal(str)
    poll_completed = Signal(int)  # total task count

    def __init__(self, bridge: Things3Bridge, interval_ms: int = DEFAULT_POLL_INTERVAL_MS, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._interval_ms = interval_ms
        self._seen_ids: Set[str] = set()
        self._stop_flag = False

    def set_interval(self, ms: int):
        self._interval_ms = max(5000, ms)  # Minimum 5 seconds

    def seed_seen_ids(self, ids: Set[str]):
        """Pre-populate seen IDs (e.g., from PrintStateDB on startup)."""
        self._seen_ids = set(ids)

    def run(self):
        """Main polling loop."""
        self._stop_flag = False
        logger.info("Poller started (interval: %dms)", self._interval_ms)

        while not self._stop_flag:
            try:
                tasks = self._bridge.get_today_tasks()
                current_ids = {t.id for t in tasks}

                # Find tasks we haven't seen before
                new_tasks = [t for t in tasks if t.id not in self._seen_ids]

                if new_tasks:
                    self._seen_ids.update(t.id for t in new_tasks)
                    self.new_tasks_found.emit(new_tasks)
                    logger.info("Found %d new tasks", len(new_tasks))

                # Update seen set with current IDs (don't remove - they might reappear)
                self._seen_ids.update(current_ids)
                self.poll_completed.emit(len(tasks))

            except Exception as e:
                logger.error("Poll error: %s", e)
                self.poll_error.emit(str(e))

            # Sleep in small increments so we can stop quickly
            elapsed = 0
            while elapsed < self._interval_ms and not self._stop_flag:
                self.msleep(500)
                elapsed += 500

        logger.info("Poller stopped")

    def stop(self):
        """Signal the poller to stop."""
        self._stop_flag = True
