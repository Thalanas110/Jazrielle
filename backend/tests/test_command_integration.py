from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import DEFAULT_SYSTEM_PROMPT_PATH, Settings
from app.modules.assistant.adapters.network import FetchedPage, SearchResult
from app.main import create_app
from app.modules.assistant.model import ModelStatus
from tests.support import FakeFetchProvider, FakeSearchProvider


class ConfiguredJsonProvider:
    def __init__(self, response: str, summary_response: str | None = None):
        self.response = response
        self.summary_response = summary_response
        self.system = None
        self.calls = []

    def status(self):
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str):
        self.calls.append((prompt, system))
        self.system = system
        if self.summary_response is not None and "SOURCE MATERIAL START" in prompt:
            return "test-model", self.summary_response
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
    url = "https://pagasa.dost.gov.ph/"
    provider = ConfiguredJsonProvider(
        '{"action":"search_google","arguments":{"query":"rainfall warning for Cebu"},"message":"Searching Google."}',
        summary_response="Cebu is under a yellow rainfall warning.",
    )
    search = FakeSearchProvider(
        [
            SearchResult(
                "PAGASA",
                url,
                "Rainfall warning information.",
            ),
        ]
    )
    fetch = FakeFetchProvider(
        {url: FetchedPage("PAGASA", url, "Current yellow rainfall warning for Cebu.")}
    )
    application = create_app(
        model_provider=provider,
        adapters=SimpleNamespace(search=search, fetch=fetch),
    )

    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "check the color coded rainfall warning for Cebu province right now"},
    )

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["message"] == "Cebu is under a yellow rainfall warning."
    assert "Web results" not in response.json()["message"]
    assert len(provider.calls) == 2
    assert "SOURCE MATERIAL START" in provider.calls[1][0]
    assert "Current yellow rainfall warning for Cebu." in provider.calls[1][0]
    assert "untrusted" in provider.calls[1][1].lower()
    assert response.json()["launchUrl"] is None


def test_google_search_without_tinyfish_key_reports_configuration():
    provider = ConfiguredJsonProvider(
        '{"action":"search_google","arguments":{"query":"rainfall warning"},"message":"Searching."}'
    )
    application = create_app(
        settings=Settings(tinyfish_api_key=None),
        model_provider=provider,
    )

    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "check the rainfall warning"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Web search is not configured. Add TINYFISH_API_KEY to backend/.env.",
        "handled": False,
        "app": None,
        "launchUrl": None,
    }
