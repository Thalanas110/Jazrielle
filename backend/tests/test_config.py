from pathlib import Path

from app.core.config import DEFAULT_SYSTEM_PROMPT_PATH, Settings


def test_settings_default_system_prompt_path_points_to_repository_prompt():
    settings = Settings()

    assert Path(settings.system_prompt_path) == DEFAULT_SYSTEM_PROMPT_PATH
    assert DEFAULT_SYSTEM_PROMPT_PATH.as_posix().endswith("ai/system-prompt.md")


def test_settings_accepts_absolute_packaged_asset_paths(monkeypatch, tmp_path):
    model = tmp_path / "ai" / "qwen.gguf"
    prompt = tmp_path / "ai" / "system-prompt.md"
    actions = tmp_path / "ai" / "assistant-actions.json"
    monkeypatch.setenv("MODEL_PATH", str(model))
    monkeypatch.setenv("SYSTEM_PROMPT_PATH", str(prompt))
    monkeypatch.setenv("ACTION_CONFIG_PATH", str(actions))

    settings = Settings()

    assert Path(settings.model_path) == model
    assert Path(settings.system_prompt_path) == prompt
    assert Path(settings.action_config_path) == actions


def test_settings_allows_tauri_production_origins():
    settings = Settings()

    assert "tauri://localhost" in settings.cors_origin_list
    assert "http://tauri.localhost" in settings.cors_origin_list
