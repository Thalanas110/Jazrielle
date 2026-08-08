from collections.abc import Callable, Mapping
from dataclasses import dataclass
import subprocess
from typing import Any

from app.modules.assistant.intent import AssistantIntent
from app.modules.assistant.schemas import Capability, CommandResult
from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.adapters.metrics import LocalMetricsAdapter, MetricsAdapter
from app.modules.assistant.adapters.media import MediaAdapter, WindowsMediaAdapter
from app.modules.assistant.adapters.network import (
    UpdateProvider,
    WeatherProvider,
    WttrWeatherProvider,
    WingetUpdateProvider,
)
from app.modules.assistant.adapters.processes import ProcessAdapter, WindowsProcessAdapter
from app.modules.assistant.adapters.reminders import JsonReminderStore, ReminderStore
from app.modules.assistant.adapters.system import LocalSystemAdapter, SystemAdapter


ActionHandler = Callable[[AssistantIntent], CommandResult | Mapping[str, Any]]


@dataclass(frozen=True)
class ActionDefinition:
    id: str
    label: str
    description: str
    examples: list[str]
    handler: ActionHandler


class UnknownActionError(ValueError):
    """Raised when an intent names no registered action."""


class ActionRegistry:
    def __init__(self, definitions: Mapping[str, ActionDefinition | ActionHandler]):
        self._definitions = {
            action_id: self._coerce_definition(action_id, definition)
            for action_id, definition in definitions.items()
        }

    def execute(self, intent: AssistantIntent) -> CommandResult:
        definition = self._definitions.get(intent.action)
        if definition is None:
            raise UnknownActionError(f"No handler is registered for {intent.action}.")
        result = definition.handler(intent)
        return result if isinstance(result, CommandResult) else CommandResult.model_validate(result)

    def get_capabilities(self) -> list[Capability]:
        return [
            Capability(
                id=definition.id,
                label=definition.label,
                description=definition.description,
                examples=definition.examples.copy(),
            )
            for definition in self._definitions.values()
        ]

    @staticmethod
    def _coerce_definition(
        action_id: str,
        definition: ActionDefinition | ActionHandler,
    ) -> ActionDefinition:
        if isinstance(definition, ActionDefinition):
            return definition
        return ActionDefinition(
            id=action_id,
            label=action_id.replace("_", " ").title(),
            description=f"Perform {action_id.replace('_', ' ')}.",
            examples=[action_id.replace("_", " ")],
            handler=definition,
        )


def build_action_registry(config: Any = None, adapters: Any = None) -> ActionRegistry:
    action_config: AssistantActionConfig = config or AssistantActionConfig()
    system: SystemAdapter = getattr(adapters, "system", None) or LocalSystemAdapter()
    metrics: MetricsAdapter = getattr(adapters, "metrics", None) or LocalMetricsAdapter()
    media: MediaAdapter = getattr(adapters, "media", None) or WindowsMediaAdapter()
    processes: ProcessAdapter = getattr(adapters, "processes", None) or WindowsProcessAdapter()
    reminders: ReminderStore = getattr(adapters, "reminders", None) or JsonReminderStore(
        action_config.settings.reminder_path
    )
    weather: WeatherProvider = getattr(adapters, "weather", None) or WttrWeatherProvider()
    updates: UpdateProvider = getattr(adapters, "updates", None) or WingetUpdateProvider()

    def cpu_usage(intent: AssistantIntent) -> CommandResult:
        del intent
        return CommandResult(message=f"CPU usage is {metrics.cpu_usage():.1f}%.", handled=True)

    def memory_usage(intent: AssistantIntent) -> CommandResult:
        del intent
        usage = metrics.memory_usage()
        return CommandResult(
            message=(
                f"Memory usage is {usage['percent']:.1f}% "
                f"({usage['used_gb']:.1f}/{usage['total_gb']:.1f} GB)."
            ),
            handled=True,
        )

    def top_processes(intent: AssistantIntent) -> CommandResult:
        raw_limit = intent.arguments.get("limit", 5)
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, int) or not 1 <= raw_limit <= 10:
            return CommandResult(message="The process limit must be between 1 and 10.", handled=False)
        rows = metrics.top_processes(raw_limit)
        formatted = ", ".join(f"{row['name']} ({float(row['memory_mb']):.1f} MB)" for row in rows)
        return CommandResult(message=f"Top processes: {formatted or 'none found'}.", handled=True)

    def open_application(intent: AssistantIntent) -> CommandResult:
        target = _configured_target(action_config.applications, intent.arguments.get("application"))
        if target is None:
            return CommandResult(message="That application is not configured.", handled=False)
        return CommandResult(message=f"Opening {target.label}.", handled=True, app=target.label)

    def close_application(intent: AssistantIntent) -> CommandResult:
        target = _configured_target(action_config.applications, intent.arguments.get("application"))
        if target is None:
            return CommandResult(message="That application is not configured.", handled=False)
        if not target.process_name:
            return CommandResult(message=f"{target.label} has no close target configured.", handled=False)
        processes.stop(target.process_name)
        return CommandResult(message=f"Closing {target.label}.", handled=True)

    def start_project(intent: AssistantIntent) -> CommandResult:
        target = _configured_target(action_config.projects, intent.arguments.get("project"))
        if target is None:
            return CommandResult(message="That project is not configured.", handled=False)
        processes.start(target.start_command.copy(), target.working_directory)
        return CommandResult(message=f"Starting {intent.arguments['project']}.", handled=True)

    def stop_project(intent: AssistantIntent) -> CommandResult:
        target = _configured_target(action_config.projects, intent.arguments.get("project"))
        if target is None:
            return CommandResult(message="That project is not configured.", handled=False)
        if not target.process_name:
            return CommandResult(message="That project has no stop target configured.", handled=False)
        processes.stop(target.process_name)
        return CommandResult(message=f"Stopping {intent.arguments['project']}.", handled=True)

    def create_reminder(intent: AssistantIntent) -> CommandResult:
        message = intent.arguments.get("message")
        due_at = intent.arguments.get("due_at") or intent.arguments.get("time")
        if not isinstance(message, str) or not message.strip() or not isinstance(due_at, str):
            return CommandResult(message="A reminder message and time are required.", handled=False)
        try:
            reminder = reminders.create(message, due_at)
        except ValueError:
            return CommandResult(message="That reminder time is not valid.", handled=False)
        return CommandResult(message=f"Reminder set for {reminder.due_at}: {reminder.message}.", handled=True)

    def list_reminders(intent: AssistantIntent) -> CommandResult:
        del intent
        values = reminders.list()
        if not values:
            return CommandResult(message="No reminders are set.", handled=True)
        formatted = "; ".join(f"{reminder.due_at}: {reminder.message}" for reminder in values)
        return CommandResult(message=f"Reminders: {formatted}.", handled=True)

    def get_weather(intent: AssistantIntent) -> CommandResult:
        location = intent.arguments.get("location") or action_config.settings.weather_location
        if not isinstance(location, str) or not location.strip():
            return CommandResult(message="A weather location is required.", handled=False)
        try:
            report = weather.get_weather(location.strip())
        except (OSError, KeyError, ValueError, TimeoutError):
            return CommandResult(message="Weather is temporarily unavailable.", handled=False)
        return CommandResult(
            message=f"{report.location}: {report.temperature_c} C, {report.description}.",
            handled=True,
        )

    def get_updates(intent: AssistantIntent) -> CommandResult:
        del intent
        try:
            message = updates.get_updates()
        except (OSError, subprocess.TimeoutExpired):
            return CommandResult(message="Updates are temporarily unavailable.", handled=False)
        return CommandResult(message=message, handled=True)

    def play_media(intent: AssistantIntent) -> CommandResult:
        del intent
        try:
            media.play()
        except RuntimeError:
            return CommandResult(message="Media controls are unavailable.", handled=False)
        return CommandResult(message="Playing media.", handled=True)

    def pause_media(intent: AssistantIntent) -> CommandResult:
        del intent
        try:
            media.pause()
        except RuntimeError:
            return CommandResult(message="Media controls are unavailable.", handled=False)
        return CommandResult(message="Pausing playback.", handled=True)

    def set_volume(intent: AssistantIntent) -> CommandResult:
        raw_level = intent.arguments.get("level", intent.arguments.get("percent"))
        if isinstance(raw_level, bool) or not isinstance(raw_level, (int, float)) or not 0 <= raw_level <= 100:
            return CommandResult(message="Volume must be between 0 and 100.", handled=False)
        level = int(raw_level)
        try:
            media.set_volume(level)
        except RuntimeError:
            return CommandResult(message="Volume controls are unavailable.", handled=False)
        return CommandResult(message=f"Volume set to {level}%.", handled=True)

    return ActionRegistry(
        {
            "conversation": ActionDefinition(
                id="conversation",
                label="Conversation",
                description="Respond to a simple conversational request.",
                examples=["how are you"],
                handler=lambda intent: CommandResult(message=intent.message, handled=True),
            ),
            "get_time": ActionDefinition(
                id="get_time",
                label="Time check",
                description="Read the current local time.",
                examples=["what time is it"],
                handler=lambda intent: CommandResult(message=f"It is {system.get_time()}.", handled=True),
            ),
            "get_date": ActionDefinition(
                id="get_date",
                label="Date check",
                description="Read the current local date.",
                examples=["what date is it"],
                handler=lambda intent: CommandResult(message=f"Today is {system.get_date()}.", handled=True),
            ),
            "get_system_status": ActionDefinition(
                id="get_system_status",
                label="System status",
                description="Report basic local system status.",
                examples=["what is the system status"],
                handler=lambda intent: CommandResult(message=system.get_system_status(), handled=True),
            ),
            "get_cpu_usage": ActionDefinition(
                id="get_cpu_usage",
                label="CPU usage",
                description="Read current CPU usage.",
                examples=["what is my CPU usage"],
                handler=cpu_usage,
            ),
            "get_memory_usage": ActionDefinition(
                id="get_memory_usage",
                label="Memory usage",
                description="Read current memory usage.",
                examples=["what is my RAM usage"],
                handler=memory_usage,
            ),
            "get_top_processes": ActionDefinition(
                id="get_top_processes",
                label="Top processes",
                description="List processes using the most memory.",
                examples=["what is using the most RAM"],
                handler=top_processes,
            ),
            "open_application": ActionDefinition(
                id="open_application",
                label="Open application",
                description="Open a configured application.",
                examples=["open calendar"],
                handler=open_application,
            ),
            "close_application": ActionDefinition(
                id="close_application",
                label="Close application",
                description="Close a configured application.",
                examples=["close spotify"],
                handler=close_application,
            ),
            "start_project": ActionDefinition(
                id="start_project",
                label="Start project",
                description="Start a configured project.",
                examples=["start the demo project"],
                handler=start_project,
            ),
            "stop_project": ActionDefinition(
                id="stop_project",
                label="Stop project",
                description="Stop a configured project.",
                examples=["stop the demo project"],
                handler=stop_project,
            ),
            "create_reminder": ActionDefinition(
                id="create_reminder",
                label="Create reminder",
                description="Create a local reminder.",
                examples=["remind me at 8 PM to submit my report"],
                handler=create_reminder,
            ),
            "list_reminders": ActionDefinition(
                id="list_reminders",
                label="List reminders",
                description="List local reminders.",
                examples=["what reminders do I have"],
                handler=list_reminders,
            ),
            "get_weather": ActionDefinition(
                id="get_weather",
                label="Weather check",
                description="Retrieve weather for a configured or requested location.",
                examples=["what is the weather"],
                handler=get_weather,
            ),
            "get_updates": ActionDefinition(
                id="get_updates",
                label="Updates check",
                description="Check for available local application updates.",
                examples=["give me an update"],
                handler=get_updates,
            ),
            "play_media": ActionDefinition(
                id="play_media",
                label="Play media",
                description="Start media playback.",
                examples=["play the music"],
                handler=play_media,
            ),
            "pause_media": ActionDefinition(
                id="pause_media",
                label="Pause media",
                description="Pause media playback.",
                examples=["pause the music"],
                handler=pause_media,
            ),
            "set_volume": ActionDefinition(
                id="set_volume",
                label="Set volume",
                description="Set system volume from 0 to 100.",
                examples=["set volume to 35"],
                handler=set_volume,
            ),
        }
    )


def _configured_target(targets: dict[str, Any], value: Any) -> Any | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return targets.get(value.strip().lower())
