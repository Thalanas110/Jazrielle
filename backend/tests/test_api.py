from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app, create_app
from app.modules.assistant.model import ModelStatus, UnavailableModelProvider


client = TestClient(app)


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
    assert {item["id"] for item in body["capabilities"]} == {"calendar", "downloads", "time"}


def test_known_command_is_handled_without_shell_execution():
    response = client.post("/api/jarvis/execute", json={"command": "what time is it"})

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["message"].startswith("It is ")


def test_unknown_command_is_reported_as_unhandled():
    response = client.post("/api/jarvis/execute", json={"command": "run arbitrary shell"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "I do not have a safe action for that command.",
        "handled": False,
        "app": None,
        "launchUrl": None,
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
    def status(self):
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str):
        return "test-model", "ok"


def test_create_app_reads_configured_system_prompt(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("custom prompt", encoding="utf-8")

    application = create_app(
        settings=Settings(system_prompt_path=str(prompt_path)),
        model_provider=ConfiguredProvider(),
    )

    assert application.state.system_prompt == "custom prompt"
