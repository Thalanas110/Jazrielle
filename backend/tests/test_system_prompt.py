from pathlib import Path

import pytest

from app.core.system_prompt import SystemPromptConfigurationError, load_system_prompt


def test_system_prompt_configuration_error_is_a_runtime_error():
    assert issubclass(SystemPromptConfigurationError, RuntimeError)


def test_load_system_prompt_reads_exact_utf8_contents(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("You are Kaelith.\nRéponds brièvement.", encoding="utf-8")

    assert load_system_prompt(prompt_path) == "You are Kaelith.\nRéponds brièvement."


def test_load_system_prompt_rejects_missing_file(tmp_path: Path):
    with pytest.raises(SystemPromptConfigurationError, match="does not exist"):
        load_system_prompt(tmp_path / "missing.md")


def test_load_system_prompt_rejects_invalid_utf8(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_bytes(b"valid text\xff")

    with pytest.raises(SystemPromptConfigurationError, match="UTF-8"):
        load_system_prompt(prompt_path)
