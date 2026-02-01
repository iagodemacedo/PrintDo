"""Things 3 integration via AppleScript on macOS."""

import locale
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Things3Task:
    """Represents a task from Things 3."""

    id: str
    name: str
    notes: str = ""
    due_date: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    project: Optional[str] = None
    status: str = "open"
    creation_date: Optional[str] = None


class Things3Service:
    """Read tasks from Things 3 via AppleScript."""

    FIELD_SEP = "|||"
    TASK_SEP = "|||TASK|||"

    @staticmethod
    def _run_applescript(script: str) -> str:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
        return result.stdout.strip()

    def get_today_tasks(self) -> List[Things3Task]:
        """Fetch all tasks from the Today list."""
        script = '''
tell application "Things3"
    set taskList to to dos of list "Today"
    set output to ""
    repeat with t in taskList
        set tid to id of t
        set tname to name of t
        set tnotes to notes of t
        set tstatus to status of t as string
        try
            set tdue to due date of t as string
        on error
            set tdue to ""
        end try
        try
            set tproject to name of project of t
        on error
            set tproject to ""
        end try
        set ttags to tag names of t
        try
            set tcreated to creation date of t as string
        on error
            set tcreated to ""
        end try
        set output to output & tid & "|||" & tname & "|||" & tnotes & "|||" & tdue & "|||" & tproject & "|||" & ttags & "|||" & tstatus & "|||" & tcreated & "|||TASK|||"
    end repeat
    return output
end tell
'''
        raw = self._run_applescript(script)
        return self._parse_tasks(raw)

    @staticmethod
    def _format_date(raw_date: str) -> str:
        """Format an AppleScript date string to weekday + date (no time).

        Tries common AppleScript date formats and outputs using the
        system locale (e.g. "sábado, 15 de fevereiro de 2025" in pt-BR).
        """
        if not raw_date:
            return ""
        # Try to set system locale for strftime output
        try:
            locale.setlocale(locale.LC_TIME, "")
        except locale.Error:
            pass
        # AppleScript "date as string" formats vary by locale; try several
        for fmt in (
            "%A, %d de %B de %Y %H:%M:%S",   # pt-BR long
            "%A, %B %d, %Y at %I:%M:%S %p",  # en-US long
            "%A, %d %B %Y %H:%M:%S",          # other
            "%d/%m/%Y %H:%M:%S",              # short numeric
        ):
            try:
                dt = datetime.strptime(raw_date.strip(), fmt)
                # "%A, %d de %B de %Y" respects LC_TIME locale
                return dt.strftime("%A, %d de %B de %Y")
            except ValueError:
                continue
        # Fallback: strip everything after last digit sequence that looks
        # like a year, dropping time portion
        import re
        m = re.match(r"(.+\d{4})", raw_date)
        return m.group(1).strip() if m else raw_date

    def _parse_tasks(self, raw: str) -> List[Things3Task]:
        tasks = []
        for block in raw.split(self.TASK_SEP):
            block = block.strip()
            if not block:
                continue
            parts = block.split(self.FIELD_SEP)
            if len(parts) >= 7:
                tags_str = parts[5].strip() if len(parts) > 5 else ""
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                tasks.append(
                    Things3Task(
                        id=parts[0].strip(),
                        name=parts[1].strip(),
                        notes=parts[2].strip(),
                        due_date=self._format_date(parts[3].strip()) or None,
                        project=parts[4].strip() or None,
                        tags=tags,
                        status=parts[6].strip(),
                        creation_date=parts[7].strip() or None if len(parts) > 7 else None,
                    )
                )
        return tasks

    def is_available(self) -> bool:
        """Check if Things 3 is installed."""
        try:
            self._run_applescript(
                'tell application "System Events" to return exists application process "Things3"'
            )
            return True
        except (RuntimeError, subprocess.TimeoutExpired):
            return False
