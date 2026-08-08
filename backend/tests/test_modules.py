import pytest

from app.main import app
from app.modules.assistant.action_registry import ActionRegistry
from app.modules.assistant.model import ModelStatus, UnavailableModelProvider
from app.modules.assistant.service import AssistantService


class ConfiguredProvider:
    def __init__(self):
        self.system = None
        self.response = None

    def status(self) -> ModelStatus:
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        self.system = system
        return "test-model", self.response or f"response to: {prompt}"


@pytest.mark.anyio
async def test_assistant_service_exposes_capabilities_and_commands():
    provider = ConfiguredProvider()
    provider.response = '{"action":"conversation","arguments":{},"message":"Understood."}'
    service = AssistantService(
        provider,
        "canonical prompt",
        action_registry=ActionRegistry({"conversation": lambda intent: {"message": intent.message, "handled": True}}),
    )

    capabilities = service.get_capabilities()
    command = await service.execute_command("what time is it")

    assert capabilities.assistant == "JAZRIELLE"
    assert capabilities.llmConfigured is True
    assert command.handled is True


@pytest.mark.anyio
async def test_execute_command_uses_canonical_prompt_and_model_intent():
    class JsonProvider:
        def __init__(self):
            self.prompt = None
            self.system = None

        def status(self) -> ModelStatus:
            return ModelStatus(configured=True, ready=True)

        async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
            self.prompt = prompt
            self.system = system
            return "test-model", '{"action":"conversation","arguments":{},"message":"Understood."}'

    provider = JsonProvider()
    registry = ActionRegistry({"conversation": lambda intent: {"message": intent.message, "handled": True}})
    service = AssistantService(provider, "canonical prompt", action_registry=registry)

    result = await service.execute_command("please acknowledge this")

    assert result.message == "Understood."
    assert provider.prompt == "please acknowledge this"
    assert provider.system == "canonical prompt"


@pytest.mark.anyio
async def test_assistant_service_returns_provider_inference():
    provider = ConfiguredProvider()

    result = await AssistantService(provider, "canonical prompt").generate_inference("hello")

    assert result.model == "test-model"
    assert result.response == "response to: hello"
    assert provider.system == "canonical prompt"


@pytest.mark.anyio
async def test_unavailable_provider_is_exposed_without_http_concerns():
    with pytest.raises(Exception) as raised:
        await AssistantService(UnavailableModelProvider(), "canonical prompt").generate_inference("hello")

    assert raised.value.__class__.__name__ == "ModelNotConfiguredError"


def test_app_composes_health_and_assistant_modules():
    paths = set(app.openapi()["paths"])

    assert {"/health", "/ready", "/api/jarvis/capabilities", "/api/jarvis/execute", "/api/jarvis/inference"} <= paths
