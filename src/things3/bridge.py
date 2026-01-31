"""AppleScript bridge to communicate with Things 3 on macOS."""

import subprocess
import logging
from datetime import datetime
from typing import List, Optional

from .models import Things3Task

logger = logging.getLogger(__name__)

# Delimiter used to separate fields in AppleScript output
FIELD_DELIM = "|||"
RECORD_DELIM = "<<<RECORD>>>"

APPLESCRIPT_GET_TODAY = '''
tell application "Things3"
    set output to ""
    set todoList to to dos of list "Today"
    repeat with t in todoList
        set taskProject to ""
        try
            set taskProject to name of project of t
        end try
        set taskArea to ""
        try
            set taskArea to name of area of t
        end try
        set taskDue to ""
        try
            set taskDue to ((due date of t) as «class isot» as string)
        end try
        set taskCreated to ""
        try
            set taskCreated to ((creation date of t) as «class isot» as string)
        end try
        set taskModified to ""
        try
            set taskModified to ((modification date of t) as «class isot» as string)
        end try
        set taskNotes to notes of t
        -- Replace newlines in notes to avoid breaking our record format
        set AppleScript's text item delimiters to {return}
        set noteItems to text items of taskNotes
        set AppleScript's text item delimiters to {"\\n"}
        set taskNotes to noteItems as text
        set AppleScript's text item delimiters to {""}

        set output to output & id of t & "|||" & name of t & "|||" & taskNotes & "|||" & taskDue & "|||" & tag names of t & "|||" & taskProject & "|||" & taskArea & "|||" & status of t & "|||" & taskCreated & "|||" & taskModified & "<<<RECORD>>>"
    end repeat
    return output
end tell
'''

APPLESCRIPT_GET_ALL_PROJECTS = '''
tell application "Things3"
    set output to ""
    repeat with p in projects
        set output to output & name of p & "<<<RECORD>>>"
    end repeat
    return output
end tell
'''

APPLESCRIPT_GET_ALL_TAGS = '''
tell application "Things3"
    set output to ""
    repeat with t in tags
        set output to output & name of t & "<<<RECORD>>>"
    end repeat
    return output
end tell
'''

APPLESCRIPT_IS_RUNNING = '''
tell application "System Events"
    set isRunning to (count of (every process whose bundle identifier is "com.culturedcode.ThingsMac")) > 0
end tell
return isRunning
'''


def _parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse an ISO date string from AppleScript."""
    if not date_str or date_str.strip() == "":
        return None
    try:
        # AppleScript «class isot» gives ISO 8601 format
        clean = date_str.strip().replace("T", " ")
        # Try various formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                continue
        # Last resort: try fromisoformat
        return datetime.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        logger.warning("Could not parse date: %s", date_str)
        return None


class Things3Bridge:
    """Bridge to communicate with Things 3 via AppleScript."""

    def _run_applescript(self, script: str) -> Optional[str]:
        """Execute an AppleScript and return the output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error("AppleScript error: %s", error_msg)
                return None
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error("osascript not found - this must run on macOS")
            return None
        except subprocess.TimeoutExpired:
            logger.error("AppleScript timed out")
            return None
        except Exception as e:
            logger.error("AppleScript execution failed: %s", e)
            return None

    def is_things3_running(self) -> bool:
        """Check if Things 3 is currently running."""
        result = self._run_applescript(APPLESCRIPT_IS_RUNNING)
        return result is not None and result.lower() == "true"

    def get_today_tasks(self) -> List[Things3Task]:
        """Fetch all tasks from Things 3 Today list."""
        raw = self._run_applescript(APPLESCRIPT_GET_TODAY)
        if raw is None:
            return []
        return self._parse_tasks(raw)

    def get_projects(self) -> List[str]:
        """Get all project names from Things 3."""
        raw = self._run_applescript(APPLESCRIPT_GET_ALL_PROJECTS)
        if raw is None:
            return []
        return [
            p.strip() for p in raw.split(RECORD_DELIM) if p.strip()
        ]

    def get_tags(self) -> List[str]:
        """Get all tag names from Things 3."""
        raw = self._run_applescript(APPLESCRIPT_GET_ALL_TAGS)
        if raw is None:
            return []
        return [
            t.strip() for t in raw.split(RECORD_DELIM) if t.strip()
        ]

    def _parse_tasks(self, raw: str) -> List[Things3Task]:
        """Parse raw AppleScript output into Things3Task objects."""
        tasks = []
        records = raw.split(RECORD_DELIM)

        for record in records:
            record = record.strip()
            if not record:
                continue

            fields = record.split(FIELD_DELIM)
            if len(fields) < 8:
                logger.warning("Skipping malformed record: %s", record[:80])
                continue

            # Parse tag names from comma-separated string
            tag_str = fields[4].strip() if len(fields) > 4 else ""
            tag_names = [t.strip() for t in tag_str.split(",") if t.strip()]

            # Parse status - Things 3 returns "open", "completed", "canceled"
            status_raw = fields[7].strip() if len(fields) > 7 else "open"

            task = Things3Task(
                id=fields[0].strip(),
                name=fields[1].strip(),
                notes=fields[2].strip().replace("\\n", "\n"),
                due_date=_parse_iso_date(fields[3]) if len(fields) > 3 else None,
                tag_names=tag_names,
                project_name=fields[5].strip() if len(fields) > 5 else "",
                area_name=fields[6].strip() if len(fields) > 6 else "",
                status=status_raw,
                creation_date=_parse_iso_date(fields[8]) if len(fields) > 8 else None,
                modification_date=_parse_iso_date(fields[9]) if len(fields) > 9 else None,
            )
            tasks.append(task)

        return tasks
