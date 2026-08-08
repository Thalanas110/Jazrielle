import pytest

from app.modules.assistant.action_registry import ActionRegistry, UnknownActionError
from app.modules.assistant.intent import AssistantIntent


def test_registry_executes_a_registered_handler():
    registry = ActionRegistry({"conversation": lambda intent: {"message": intent.message, "handled": True}})

    result = registry.execute(
        AssistantIntent(action="conversation", arguments={}, message="Hello.")
    )

    assert result.handled is True
    assert result.message == "Hello."


def test_registry_rejects_unregistered_actions():
    registry = ActionRegistry({})

    with pytest.raises(UnknownActionError):
        registry.execute(AssistantIntent(action="get_time", arguments={}, message="Checking."))
