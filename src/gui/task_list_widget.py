"""Task list widget showing Things 3 Today tasks with checkboxes."""

import logging
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.things3.models import Things3Task

logger = logging.getLogger(__name__)


class TaskItemWidget(QWidget):
    """Custom widget for a single task in the list."""

    checked_changed = Signal(bool)

    def __init__(self, task: Things3Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("taskItem")
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(
            lambda state: self.checked_changed.emit(state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.checkbox)

        # Task info (vertical)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Top row: name
        name_label = QLabel(self.task.name)
        name_label.setObjectName("taskName")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        # Bottom row: project + tags
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(6)

        if self.task.project_name:
            project_label = QLabel(self.task.project_name)
            project_label.setObjectName("taskProject")
            meta_layout.addWidget(project_label)

        for tag in self.task.tag_names[:3]:  # Show max 3 tags
            tag_label = QLabel(tag)
            tag_label.setObjectName("taskTag")
            meta_layout.addWidget(tag_label)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        layout.addLayout(info_layout, stretch=1)

        # Due date (right side)
        if self.task.due_date:
            due_label = QLabel(self.task.due_date_short)
            due_label.setObjectName("taskDueDate")
            due_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(due_label)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)


class TaskListWidget(QListWidget):
    """List of Things 3 Today tasks with checkboxes for selection."""

    task_selected = Signal(object)  # Emits Things3Task when clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_widgets: List[TaskItemWidget] = []
        self.currentItemChanged.connect(self._on_item_changed)

    def set_tasks(self, tasks: List[Things3Task]):
        """Replace the task list with new tasks."""
        self.clear()
        self._task_widgets = []

        for task in tasks:
            if task.status == "completed":
                continue  # Skip completed tasks

            item_widget = TaskItemWidget(task)
            self._task_widgets.append(item_widget)

            list_item = QListWidgetItem(self)
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, task)
            self.addItem(list_item)
            self.setItemWidget(list_item, item_widget)

    def get_checked_tasks(self) -> List[Things3Task]:
        """Return all checked tasks."""
        checked = []
        for widget in self._task_widgets:
            if widget.is_checked():
                checked.append(widget.task)
        return checked

    def get_all_tasks(self) -> List[Things3Task]:
        """Return all tasks in the list."""
        return [w.task for w in self._task_widgets]

    def select_all(self):
        for w in self._task_widgets:
            w.set_checked(True)

    def deselect_all(self):
        for w in self._task_widgets:
            w.set_checked(False)

    def _on_item_changed(self, current: QListWidgetItem, _previous):
        if current is not None:
            task = current.data(Qt.ItemDataRole.UserRole)
            if task:
                self.task_selected.emit(task)

    @property
    def task_count(self) -> int:
        return len(self._task_widgets)
