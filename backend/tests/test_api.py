from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_a_live_api():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_api_up_but_model_not_configured():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_configured": False}


def test_capabilities_match_the_frontend_contract():
    response = client.get("/api/jarvis/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["assistant"] == "KAELITH"
    assert body["localMode"] is True
    assert body["llmConfigured"] is False
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
    response = client.post(
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
