from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.action_registry import build_action_registry
from tests.support import intent


class FakeSystemAdapter:
    def __init__(self, *, time: str = "11:30 PM", date: str = "Saturday, August 8, 2026", status: str = "Windows ready"):
        self._time = time
        self._date = date
        self._status = status

    def get_time(self) -> str:
        return self._time

    def get_date(self) -> str:
        return self._date

    def get_system_status(self) -> str:
        return self._status


def test_get_time_uses_system_adapter():
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(system=FakeSystemAdapter(time="11:30 PM")),
    )

    result = registry.execute(intent("get_time"))

    assert result.handled is True
    assert result.message == "It is 11:30 PM."


def test_get_date_and_system_status_use_system_adapter():
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(system=FakeSystemAdapter()),
    )

    assert registry.execute(intent("get_date")).message == "Today is Saturday, August 8, 2026."
    assert registry.execute(intent("get_system_status")).message == "Windows ready"
