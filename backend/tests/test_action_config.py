import json

import pytest

from app.core.config import DEFAULT_ACTION_CONFIG_PATH
from app.modules.assistant.action_config import ConfigError, load_action_config


def test_load_action_config_resolves_declared_targets(tmp_path):
    config_path = tmp_path / "assistant-actions.json"
    config_path.write_text(
        json.dumps(
            {
                "applications": {"calendar": {"label": "Calendar", "launchTarget": "Calendar"}},
                "projects": {
                    "demo": {
                        "workingDirectory": str(tmp_path),
                        "startCommand": ["python", "-m", "demo"],
                    }
                },
                "settings": {"projectRoot": str(tmp_path)},
            }
        ),
        encoding="utf-8",
    )

    config = load_action_config(config_path)

    assert config.applications["calendar"].launch_target == "Calendar"
    assert config.settings.project_root == tmp_path.resolve()
    assert config.projects["demo"].working_directory == tmp_path.resolve()
    assert config.projects["demo"].start_command == ["python", "-m", "demo"]


def test_load_action_config_rejects_project_with_missing_directory(tmp_path):
    config_path = tmp_path / "assistant-actions.json"
    config_path.write_text(
        json.dumps(
            {
                "projects": {
                    "bad": {
                        "workingDirectory": str(tmp_path / "missing"),
                        "startCommand": ["python"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_action_config(config_path)


def test_load_action_config_rejects_project_outside_allowlisted_root(tmp_path):
    allowed_root = tmp_path / "development"
    allowed_root.mkdir()
    outside_project = tmp_path / "outside"
    outside_project.mkdir()
    config_path = tmp_path / "assistant-actions.json"
    config_path.write_text(
        json.dumps(
            {
                "settings": {"projectRoot": str(allowed_root)},
                "projects": {
                    "bad": {
                        "workingDirectory": str(outside_project),
                        "startCommand": ["code", "."],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="outside the configured project root"):
        load_action_config(config_path)


def test_load_action_config_discovers_projects_when_project_map_is_empty(tmp_path):
    root = tmp_path / "development"
    repository = root / "personal" / "demo"
    (repository / ".git").mkdir(parents=True)
    config_path = tmp_path / "assistant-actions.json"
    config_path.write_text(
        json.dumps(
            {
                "projects": {},
                "settings": {"projectRoot": str(root)},
            }
        ),
        encoding="utf-8",
    )

    config = load_action_config(config_path)

    assert config.projects["demo"].working_directory == repository.resolve()
    assert config.projects["demo"].start_command == [
        "cmd.exe", "/d", "/s", "/c", "code.cmd ."
    ]
    assert config.projects["demo"].process_name == "Code.exe"


def test_default_projects_are_vscode_targets_inside_development_root():
    config = load_action_config(DEFAULT_ACTION_CONFIG_PATH)

    assert config.settings.project_root.name == "development"
    assert set(config.projects) == {
        "tda car rental",
        "icarewebsitenew",
        "stagedeck",
        "jazrielle",
        "botchabuster",
        "examhub",
        "meatlens-training-2",
    }
    assert all(
        project.start_command == ["cmd.exe", "/d", "/s", "/c", "code.cmd ."]
        for project in config.projects.values()
    )
    assert all(
        project.working_directory.is_relative_to(config.settings.project_root)
        for project in config.projects.values()
    )
