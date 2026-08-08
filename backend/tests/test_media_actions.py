from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.action_registry import build_action_registry
from tests.support import intent


class FakeMediaAdapter:
    def __init__(self):
        self.calls = []

    def play(self) -> None:
        self.calls.append(("play",))

    def pause(self) -> None:
        self.calls.append(("pause",))

    def set_volume(self, percent: int) -> None:
        self.calls.append(("volume", percent))


def test_play_pause_and_volume_use_media_adapter():
    adapter = FakeMediaAdapter()
    registry = build_action_registry(AssistantActionConfig(), SimpleNamespace(media=adapter))

    assert registry.execute(intent("play_media")).handled is True
    assert registry.execute(intent("pause_media")).handled is True
    assert registry.execute(intent("set_volume", {"level": 35})).handled is True
    assert adapter.calls == [("play",), ("pause",), ("volume", 35)]


def test_set_volume_rejects_values_outside_zero_to_hundred():
    adapter = FakeMediaAdapter()
    registry = build_action_registry(AssistantActionConfig(), SimpleNamespace(media=adapter))

    result = registry.execute(intent("set_volume", {"level": 120}))

    assert result.handled is False
    assert adapter.calls == []
