from pathlib import Path


class SystemPromptConfigurationError(RuntimeError):
    """Raised when the configured system prompt cannot be loaded."""


def load_system_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise SystemPromptConfigurationError(
            f"System prompt file does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise SystemPromptConfigurationError(
            f"System prompt file is not valid UTF-8: {path}"
        ) from error
    except OSError as error:
        raise SystemPromptConfigurationError(
            f"System prompt file cannot be read: {path}"
        ) from error
