from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import DEFAULT_SYSTEM_PROMPT_PATH, Settings
from app.core.system_prompt import SystemPromptConfigurationError
from app.main import app, create_app
from app.modules.assistant.model import ModelStatus, UnavailableModelProvider


client = TestClient(app)


class ConfiguredJsonProvider:
    def __init__(self, response: str):
        self.response = response
        self.system = None
        self.prompt = None

    def status(self):
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str):
        self.prompt = prompt
        self.system = system
        return "test-model", self.response


def test_health_reports_a_live_api():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_api_up_but_model_not_configured():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_configured": True}


def test_capabilities_match_the_frontend_contract():
    response = client.get("/api/jarvis/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["assistant"] == "JAZRIELLE"
    assert body["localMode"] is True
    assert body["llmConfigured"] is True
    assert {"conversation", "get_time", "get_date", "get_system_status"} <= {
        item["id"] for item in body["capabilities"]
    }


def test_known_command_is_interpreted_without_shell_execution():
    application = create_app(
        model_provider=ConfiguredJsonProvider(
            '{"action":"conversation","arguments":{},"message":"The time action was selected."}'
        )
    )
    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "what time is it"},
    )

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["message"] == "The time action was selected."


def test_natural_language_command_is_interpreted_by_model():
    application = create_app(
        model_provider=ConfiguredJsonProvider(
            '{"action":"conversation","arguments":{},"message":"I understand."}'
        )
    )

    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "please acknowledge this"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "I understand."


def test_malformed_model_intent_is_reported_as_a_structured_error():
    application = create_app(model_provider=ConfiguredJsonProvider("not-json"))
    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "run arbitrary shell"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "INVALID_MODEL_INTENT",
            "message": "I couldn't understand that request.",
        }
    }


def test_inference_reports_model_not_configured():
    unavailable_client = TestClient(create_app(model_provider=UnavailableModelProvider()))
    response = unavailable_client.post(
        "/api/jarvis/inference",
        json={"prompt": "Say hello", "system": "Be brief."},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "MODEL_NOT_CONFIGURED",
            "message": "A local language model is not configured.",
        }
    }


class ConfiguredProvider:
    def __init__(self):
        self.system = None

    def status(self):
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str):
        self.system = system
        return "test-model", "ok"


def test_create_app_reads_configured_system_prompt(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("custom prompt", encoding="utf-8")

    application = create_app(
        settings=Settings(system_prompt_path=str(prompt_path)),
        model_provider=ConfiguredProvider(),
    )

    assert application.state.system_prompt == "custom prompt"


def test_inference_ignores_request_system_prompt(tmp_path: Path):
    provider = ConfiguredProvider()
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("file prompt", encoding="utf-8")
    client = TestClient(create_app(
        settings=Settings(system_prompt_path=str(prompt_path)),
        model_provider=provider,
    ))

    response = client.post(
        "/api/jarvis/inference",
        json={"prompt": "hello", "system": "caller override"},
    )

    assert response.status_code == 200
    assert provider.system == "file prompt"


def test_create_app_fails_when_system_prompt_is_missing(tmp_path: Path):
    with pytest.raises(SystemPromptConfigurationError, match="does not exist"):
        create_app(settings=Settings(system_prompt_path=str(tmp_path / "missing.md")))


def test_default_app_loads_repository_system_prompt():
    assert app.state.system_prompt == DEFAULT_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
