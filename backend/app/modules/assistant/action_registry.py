from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
import re
import subprocess
from typing import Any
from urllib.parse import urlparse

from app.modules.assistant.intent import AssistantIntent
from app.modules.assistant.schemas import Capability, CommandResult
from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.adapters.metrics import LocalMetricsAdapter, MetricsAdapter
from app.modules.assistant.adapters.media import MediaAdapter, WindowsMediaAdapter
from app.modules.assistant.adapters.network import (
    FetchProvider,
    SearchNotConfiguredError,
    SearchProvider,
    TinyFishFetchProvider,
    TinyFishSearchProvider,
    UpdateProvider,
    WeatherProvider,
    WttrWeatherProvider,
    WingetUpdateProvider,
)
from app.modules.assistant.adapters.git import GitAdapter, LocalGitAdapter
from app.modules.assistant.adapters.processes import ProcessAdapter, WindowsProcessAdapter
from app.modules.assistant.adapters.reminders import JsonReminderStore, ReminderStore
from app.modules.assistant.adapters.system import LocalSystemAdapter, SystemAdapter


ActionHandler = Callable[[AssistantIntent], CommandResult | Mapping[str, Any]]

_SEARCH_MAX_RESULTS = 2
_SEARCH_MAX_EXCERPT_CHARS = 650
_SEARCH_MAX_MESSAGE_CHARS = 1000


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
    def __init__(
        self,
        definitions: Mapping[str, ActionDefinition | ActionHandler],
        project_identifiers: Iterable[str] = (),
    ):
        self._definitions = {
            action_id: self._coerce_definition(action_id, definition)
            for action_id, definition in definitions.items()
        }
        self._project_identifiers = tuple(sorted(set(project_identifiers)))

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

    def get_project_prompt_context(self) -> str:
        if not self._project_identifiers:
            return ""
        lines = "\n".join(f"- {identifier}" for identifier in self._project_identifiers)
        return f"Configured project identifiers:\n{lines}"

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


def build_action_registry(
    config: Any = None,
    adapters: Any = None,
    *,
    tinyfish_api_key: str | None = None,
    tinyfish_location: str = "PH",
    tinyfish_language: str = "en",
) -> ActionRegistry:
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
    search: SearchProvider = getattr(adapters, "search", None) or TinyFishSearchProvider(
        tinyfish_api_key,
        location=tinyfish_location,
        language=tinyfish_language,
    )
    fetch: FetchProvider = getattr(adapters, "fetch", None) or TinyFishFetchProvider(tinyfish_api_key)
    git: GitAdapter = getattr(adapters, "git", None) or LocalGitAdapter()

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

    def open_url(intent: AssistantIntent) -> CommandResult:
        value = intent.arguments.get("url")
        if not isinstance(value, str):
            return CommandResult(message="A web URL is required.", handled=False)
        parsed = urlparse(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            return CommandResult(message="Only standard web URLs can be opened.", handled=False)
        return CommandResult(message=f"Opening {parsed.netloc}.", handled=True, launchUrl=value.strip())

    def search_google(intent: AssistantIntent) -> CommandResult:
        value = intent.arguments.get("query")
        if not isinstance(value, str) or not value.strip():
            return CommandResult(message="A Google search query is required.", handled=False)
        query = value.strip()
        try:
            results = search.search(query)
        except SearchNotConfiguredError:
            return CommandResult(
                message="Web search is not configured. Add TINYFISH_API_KEY to backend/.env.",
                handled=False,
            )
        except (OSError, TimeoutError, ValueError):
            return CommandResult(message="Web search is temporarily unavailable.", handled=False)
        if not results:
            return CommandResult(message=f'No web results found for "{query}".', handled=True)
        try:
            fetched_pages = fetch.fetch([result.url for result in results[:_SEARCH_MAX_RESULTS]], query)
        except (OSError, SearchNotConfiguredError, TimeoutError, ValueError):
            fetched_pages = {}
        summaries = []
        for result in results[:_SEARCH_MAX_RESULTS]:
            page = fetched_pages.get(result.url)
            content = page.text if page is not None else result.snippet
            compact_content = _search_excerpt(content, query)
            summary = f"{result.title}: {compact_content}" if compact_content else result.title
            summaries.append(f"{summary} ({result.url})")
        message = f'Web results for "{query}": ' + "; ".join(summaries)
        return CommandResult(
            message=message[:_SEARCH_MAX_MESSAGE_CHARS].rstrip(),
            handled=True,
        )

    def git_status(intent: AssistantIntent) -> CommandResult:
        del intent
        message = git.status(action_config.settings.repository_path)
        return CommandResult(message=message or "No Git status returned.", handled=True)

    project_examples = (
        [f"open VS Code on {project}" for project in action_config.projects]
        or ["start the demo project"]
    )

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
                examples=project_examples,
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
            "open_url": ActionDefinition(
                id="open_url",
                label="Open URL",
                description="Open a validated web URL.",
                examples=["open https://example.com"],
                handler=open_url,
            ),
            "search_google": ActionDefinition(
                id="search_google",
                label="Web search",
                description="Search the web and fetch result text without opening a browser.",
                examples=["search the web for rainfall warnings"],
                handler=search_google,
            ),
            "git_status": ActionDefinition(
                id="git_status",
                label="Git status",
                description="Read status for the configured repository.",
                examples=["show git status"],
                handler=git_status,
            ),
        },
        project_identifiers=action_config.projects.keys(),
    )


def _configured_target(targets: dict[str, Any], value: Any) -> Any | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return targets.get(value.strip().lower())


def _search_excerpt(text: str, query: str) -> str:
    compact_text = " ".join(text.split())
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not query_terms:
        return compact_text[:_SEARCH_MAX_EXCERPT_CHARS].rstrip()

    segments = [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+|\s{2,}", compact_text)
        if segment.strip()
    ]
    ranked_segments = []
    for index, segment in enumerate(segments):
        segment_terms = re.findall(r"[a-z0-9]+", segment.lower())
        score = sum(segment_terms.count(term) for term in query_terms)
        if score:
            ranked_segments.append((score, index, segment))
    if not ranked_segments:
        return compact_text[:_SEARCH_MAX_EXCERPT_CHARS].rstrip()

    selected = sorted(ranked_segments, key=lambda item: (-item[0], item[1]))[:3]
    selected.sort(key=lambda item: item[1])
    return " ".join(item[2] for item in selected)[:_SEARCH_MAX_EXCERPT_CHARS].rstrip()
