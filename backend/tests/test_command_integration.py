from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import DEFAULT_SYSTEM_PROMPT_PATH
from app.modules.assistant.adapters.network import SearchResult
from app.main import create_app
from app.modules.assistant.model import ModelStatus
from tests.support import FakeSearchProvider


class ConfiguredJsonProvider:
    def __init__(self, response: str):
        self.response = response
        self.system = None

    def status(self):
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str):
        del prompt
        self.system = system
        return "test-model", self.response


class FakeSystemAdapter:
    def get_time(self) -> str:
        return "11:30 PM"

    def get_date(self) -> str:
        return "Saturday, August 8, 2026"

    def get_system_status(self) -> str:
        return "Windows ready"


def test_command_route_uses_prompt_intent_and_registered_handler():
    provider = ConfiguredJsonProvider(
        '{"action":"get_time","arguments":{},"message":"Checking the time."}'
    )
    application = create_app(
        model_provider=provider,
        adapters=SimpleNamespace(system=FakeSystemAdapter()),
    )

    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "tell me the time"},
    )

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["message"] == "It is 11:30 PM."
    canonical_prompt = DEFAULT_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    assert provider.system.startswith(canonical_prompt)
    assert "Configured project identifiers:" in provider.system


def test_google_search_command_returns_text_without_opening_a_browser():
    provider = ConfiguredJsonProvider(
        '{"action":"search_google","arguments":{"query":"rainfall warning for Cebu"},"message":"Searching Google."}'
    )
    search = FakeSearchProvider(
        [
            SearchResult(
                "PAGASA",
                "https://pagasa.dost.gov.ph/",
                "Rainfall warning information.",
            ),
        ]
    )
    application = create_app(
        model_provider=provider,
        adapters=SimpleNamespace(search=search),
    )

    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "check the color coded rainfall warning for Cebu province right now"},
    )

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert "PAGASA" in response.json()["message"]
    assert response.json()["launchUrl"] is None
