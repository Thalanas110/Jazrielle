import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class ConfigError(ValueError):
    """Raised when the configured assistant targets are invalid."""


class ApplicationTarget(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: str = Field(min_length=1)
    launch_target: str = Field(alias="launchTarget", min_length=1)
    process_name: str | None = Field(default=None, alias="processName")


class ProjectTarget(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    working_directory: Path = Field(alias="workingDirectory")
    start_command: list[str] = Field(alias="startCommand", min_length=1)
    process_name: str | None = Field(default=None, alias="processName")

    @field_validator("start_command")
    @classmethod
    def validate_start_command(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("startCommand cannot contain empty arguments")
        return value


class ActionSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_root: Path = Field(default=Path("../../../"), alias="projectRoot")
    reminder_path: Path = Field(default=Path("reminders.json"), alias="reminderPath")
    weather_location: str = Field(default="Manila, Philippines", alias="weatherLocation", min_length=1)
    repository_path: Path = Field(default=Path(".."), alias="repositoryPath")


class AssistantActionConfig(BaseModel):
    applications: dict[str, ApplicationTarget] = Field(default_factory=dict)
    projects: dict[str, ProjectTarget] = Field(default_factory=dict)
    settings: ActionSettings = Field(default_factory=ActionSettings)


def load_action_config(path: Path) -> AssistantActionConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        config = AssistantActionConfig.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as error:
        raise ConfigError(f"Invalid assistant action configuration: {path}") from error

    base_dir = path.resolve().parent
    config.settings.project_root = _resolve_existing_directory(config.settings.project_root, base_dir)
    for project_name, project in config.projects.items():
        project.working_directory = _resolve_existing_directory(project.working_directory, base_dir)
        if not project.working_directory.is_relative_to(config.settings.project_root):
            raise ConfigError(
                f"Configured project outside the configured project root: {project_name}"
            )
    config.settings.reminder_path = _resolve_path(config.settings.reminder_path, base_dir)
    config.settings.repository_path = _resolve_existing_directory(config.settings.repository_path, base_dir)
    return config


def _resolve_path(value: Path, base_dir: Path) -> Path:
    return value if value.is_absolute() else (base_dir / value).resolve()


def _resolve_existing_directory(value: Path, base_dir: Path) -> Path:
    resolved = _resolve_path(value, base_dir)
    if not resolved.is_dir():
        raise ConfigError(f"Configured directory does not exist: {resolved}")
    return resolved
