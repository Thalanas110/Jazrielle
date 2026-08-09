from pathlib import Path
from types import SimpleNamespace

from app.core.config import DEFAULT_ACTION_CONFIG_PATH
from app.modules.assistant.action_config import (
    ApplicationTarget,
    AssistantActionConfig,
    ProjectTarget,
    load_action_config,
)
from app.modules.assistant.action_registry import build_action_registry
from tests.support import intent


class FakeProcessAdapter:
    def __init__(self):
        self.calls = []

    def start(self, command: list[str], working_directory: Path) -> None:
        self.calls.append(("start", command, working_directory))

    def stop(self, process_name: str) -> None:
        self.calls.append(("stop", process_name))


def config_with_targets(tmp_path: Path) -> AssistantActionConfig:
    return AssistantActionConfig(
        applications={
            "calendar": ApplicationTarget(label="Calendar", launchTarget="Calendar"),
            "spotify": ApplicationTarget(
                label="Spotify",
                launchTarget="Spotify",
                processName="Spotify.exe",
            ),
        },
        projects={
            "demo": ProjectTarget(
                workingDirectory=tmp_path,
                startCommand=["python", "-m", "demo"],
                processName="demo.exe",
            )
        },
    )


def test_open_application_returns_only_configured_target(tmp_path):
    processes = FakeProcessAdapter()
    registry = build_action_registry(
        config_with_targets(tmp_path),
        SimpleNamespace(processes=processes),
    )

    result = registry.execute(intent("open_application", {"application": "calendar"}))

    assert result.handled is True
    assert result.app == "Calendar"
    assert processes.calls == []


def test_unknown_application_is_not_executed(tmp_path):
    processes = FakeProcessAdapter()
    registry = build_action_registry(
        config_with_targets(tmp_path),
        SimpleNamespace(processes=processes),
    )

    result = registry.execute(intent("open_application", {"application": "powershell"}))

    assert result.handled is False
    assert processes.calls == []


def test_start_and_stop_project_use_configured_values(tmp_path):
    processes = FakeProcessAdapter()
    registry = build_action_registry(
        config_with_targets(tmp_path),
        SimpleNamespace(processes=processes),
    )

    start = registry.execute(intent("start_project", {"project": "demo"}))
    stop = registry.execute(intent("stop_project", {"project": "demo"}))

    assert start.handled is True
    assert stop.handled is True
    assert processes.calls == [
        ("start", ["python", "-m", "demo"], tmp_path),
        ("stop", "demo.exe"),
    ]


def test_default_jazrielle_project_uses_fixed_vscode_command():
    processes = FakeProcessAdapter()
    config = load_action_config(DEFAULT_ACTION_CONFIG_PATH)
    registry = build_action_registry(config, SimpleNamespace(processes=processes))

    result = registry.execute(intent("start_project", {"project": "jazrielle"}))

    assert result.handled is True
    assert result.message == "Starting jazrielle."
    assert processes.calls == [
        (
            "start",
            ["cmd.exe", "/d", "/s", "/c", "code.cmd ."],
            config.projects["jazrielle"].working_directory,
        )
    ]
