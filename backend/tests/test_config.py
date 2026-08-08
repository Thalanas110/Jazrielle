from pathlib import Path

from app.core.config import DEFAULT_SYSTEM_PROMPT_PATH, Settings


def test_settings_default_system_prompt_path_points_to_repository_prompt():
    settings = Settings()

    assert Path(settings.system_prompt_path) == DEFAULT_SYSTEM_PROMPT_PATH
    assert DEFAULT_SYSTEM_PROMPT_PATH.as_posix().endswith("ai/system-prompt.md")
