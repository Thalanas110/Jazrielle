from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


class Reminder(BaseModel):
    id: str
    message: str = Field(min_length=1)
    due_at: str = Field(min_length=1)
    created_at: str


class ReminderStore(Protocol):
    def create(self, message: str, due_at: str) -> Reminder: ...

    def list(self) -> list[Reminder]: ...


class JsonReminderStore:
    def __init__(self, path: Path):
        self._path = path

    def create(self, message: str, due_at: str) -> Reminder:
        reminder = Reminder(
            id=str(uuid4()),
            message=message.strip(),
            due_at=_normalize_due_at(due_at),
            created_at=datetime.now().astimezone().isoformat(),
        )
        reminders = self.list()
        reminders.append(reminder)
        self._write(reminders)
        return reminder

    def list(self) -> list[Reminder]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [Reminder.model_validate(item) for item in payload]

    def _write(self, reminders: list[Reminder]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temporary.write_text(
            json.dumps([reminder.model_dump() for reminder in reminders], indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._path)


def _normalize_due_at(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Reminder time is required")
    if len(candidate) == 5 and candidate[2] == ":":
        datetime.strptime(candidate, "%H:%M")
        return candidate
    return datetime.fromisoformat(candidate).isoformat()
