from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.action_registry import build_action_registry
from app.modules.assistant.adapters.reminders import JsonReminderStore
from tests.support import intent


def test_create_and_list_reminder_round_trip(tmp_path):
    store = JsonReminderStore(tmp_path / "reminders.json")

    created = store.create("Submit report", "2030-01-01T20:00:00+08:00")

    assert store.list()[0].message == created.message == "Submit report"
    assert store.list()[0].due_at == "2030-01-01T20:00:00+08:00"


class FakeReminderStore:
    def __init__(self):
        self.created = []

    def create(self, message: str, due_at: str):
        self.created.append((message, due_at))
        return SimpleNamespace(message=message, due_at=due_at)

    def list(self):
        return [SimpleNamespace(message="Submit report", due_at="20:00")]


def test_reminder_actions_use_injected_store():
    store = FakeReminderStore()
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(reminders=store),
    )

    created = registry.execute(intent("create_reminder", {"message": "Submit report", "time": "20:00"}))
    listed = registry.execute(intent("list_reminders"))

    assert created.handled is True
    assert store.created == [("Submit report", "20:00")]
    assert listed.handled is True
    assert "Submit report" in listed.message
