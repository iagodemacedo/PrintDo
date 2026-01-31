"""Data models for Things 3 tasks."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Things3Task:
    """Represents a task from Things 3."""

    id: str = ""
    name: str = ""
    notes: str = ""
    due_date: Optional[datetime] = None
    tag_names: List[str] = field(default_factory=list)
    project_name: str = ""
    area_name: str = ""
    status: str = "open"
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None

    @property
    def due_date_formatted(self) -> str:
        """Format due date for display."""
        if not self.due_date:
            return "No deadline"
        day = self.due_date.day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]
        return self.due_date.strftime(f"%B {day}{suffix}")

    @property
    def due_date_short(self) -> str:
        """Short due date format."""
        if not self.due_date:
            return ""
        return self.due_date.strftime("%b %d")

    @property
    def tags_display(self) -> str:
        """Comma-separated tags for display."""
        return ", ".join(self.tag_names) if self.tag_names else ""

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    def to_template_context(self) -> dict:
        """Convert to dict for Jinja2 template rendering."""
        return {
            "id": self.id,
            "name": self.name,
            "notes": self.notes,
            "due_date": self.due_date_formatted,
            "due_date_short": self.due_date_short,
            "due_date_raw": self.due_date,
            "tag_names": self.tag_names,
            "tags_display": self.tags_display,
            "project_name": self.project_name,
            "area_name": self.area_name,
            "status": self.status,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
        }
