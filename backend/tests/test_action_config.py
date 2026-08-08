import json

import pytest

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
            }
        ),
        encoding="utf-8",
    )

    config = load_action_config(config_path)

    assert config.applications["calendar"].launch_target == "Calendar"
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
