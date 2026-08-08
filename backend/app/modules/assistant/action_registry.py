from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.modules.assistant.intent import AssistantIntent
from app.modules.assistant.schemas import Capability, CommandResult
from app.modules.assistant.adapters.metrics import LocalMetricsAdapter, MetricsAdapter
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
    del config
    system: SystemAdapter = getattr(adapters, "system", None) or LocalSystemAdapter()
    metrics: MetricsAdapter = getattr(adapters, "metrics", None) or LocalMetricsAdapter()

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
        }
    )
