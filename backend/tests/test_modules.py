import pytest

from app.main import app
from app.modules.assistant.model import ModelStatus, UnavailableModelProvider
from app.modules.assistant.service import AssistantService


class ConfiguredProvider:
    def status(self) -> ModelStatus:
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        return "test-model", f"response to: {prompt}"


def test_assistant_service_exposes_capabilities_and_commands():
    service = AssistantService(ConfiguredProvider())

    capabilities = service.get_capabilities()
    command = service.execute_command("what time is it")

    assert capabilities.assistant == "JAZRIELLE"
    assert capabilities.llmConfigured is True
    assert command.handled is True


@pytest.mark.anyio
async def test_assistant_service_returns_provider_inference():
    result = await AssistantService(ConfiguredProvider()).generate_inference("hello", "be brief")

    assert result.model == "test-model"
    assert result.response == "response to: hello"


@pytest.mark.anyio
async def test_unavailable_provider_is_exposed_without_http_concerns():
    with pytest.raises(Exception) as raised:
        await AssistantService(UnavailableModelProvider()).generate_inference("hello", "")

    assert raised.value.__class__.__name__ == "ModelNotConfiguredError"


def test_app_composes_health_and_assistant_modules():
    paths = set(app.openapi()["paths"])

    assert {"/health", "/ready", "/api/jarvis/capabilities", "/api/jarvis/execute", "/api/jarvis/inference"} <= paths
