from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.modules.assistant.intent import AssistantIntent
from app.modules.assistant.schemas import Capability, CommandResult


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
    del config, adapters
    return ActionRegistry(
        {
            "conversation": ActionDefinition(
                id="conversation",
                label="Conversation",
                description="Respond to a simple conversational request.",
                examples=["how are you"],
                handler=lambda intent: CommandResult(message=intent.message, handled=True),
            )
        }
    )
