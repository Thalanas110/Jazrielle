from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.action_registry import build_action_registry
from tests.support import intent


class FakeMetricsAdapter:
    def __init__(self, top=None):
        self.top = top or [{"name": "python", "memory_mb": 120.0}]

    def cpu_usage(self) -> float:
        return 42.5

    def memory_usage(self) -> dict[str, float]:
        return {"percent": 61.2, "used_gb": 9.8, "total_gb": 16.0}

    def top_processes(self, limit: int):
        return self.top[:limit]


def test_top_processes_limits_and_formats_results():
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(metrics=FakeMetricsAdapter()),
    )

    result = registry.execute(intent("get_top_processes", {"limit": 1}))

    assert result.handled is True
    assert "python" in result.message


def test_set_of_resource_actions_uses_metrics_adapter():
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(metrics=FakeMetricsAdapter()),
    )

    assert registry.execute(intent("get_cpu_usage")).message == "CPU usage is 42.5%."
    assert registry.execute(intent("get_memory_usage")).message == "Memory usage is 61.2% (9.8/16.0 GB)."


def test_top_processes_rejects_invalid_limits():
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(metrics=FakeMetricsAdapter()),
    )

    result = registry.execute(intent("get_top_processes", {"limit": 100}))

    assert result.handled is False
