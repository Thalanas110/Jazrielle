from pathlib import Path
from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.adapters.network import FetchedPage, SearchResult
from app.modules.assistant.action_registry import build_action_registry
from tests.support import FakeFetchProvider, FakeSearchProvider, intent


class FakeGitAdapter:
    def __init__(self, output: str):
        self.output = output
        self.repository = None

    def status(self, repository: Path) -> str:
        self.repository = repository
        return self.output


def test_open_url_rejects_non_web_schemes():
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main")),
    ).execute(intent("open_url", {"url": "file:///secret.txt"}))

    assert result.handled is False
    assert result.launchUrl is None


def test_open_url_returns_validated_web_url():
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main")),
    ).execute(intent("open_url", {"url": "https://example.com/help"}))

    assert result.handled is True
    assert result.launchUrl == "https://example.com/help"


def test_search_google_returns_results_without_a_launch_url():
    url = "https://pagasa.dost.gov.ph/"
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
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main"), search=search, fetch=fetch),
    ).execute(intent("search_google", {"query": "color coded rainfall warning for Cebu"}))

    assert result.handled is True
    assert "Current yellow rainfall warning for Cebu." in result.message
    assert result.launchUrl is None
    assert search.query == "color coded rainfall warning for Cebu"
    assert fetch.urls == [url]
    assert fetch.purpose == "color coded rainfall warning for Cebu"


def test_search_google_rejects_an_empty_query_without_searching():
    search = FakeSearchProvider([])
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main"), search=search),
    ).execute(intent("search_google", {"query": "  "}))

    assert result.handled is False
    assert search.query is None


def test_search_google_returns_a_short_relevant_warning_excerpt():
    url = "https://pagasa.dost.gov.ph/"
    search = FakeSearchProvider(
        [SearchResult("PAGASA", url, "Rainfall warning information.")]
    )
    fetch = FakeFetchProvider(
        {
            url: FetchedPage(
                "PAGASA",
                url,
                " ".join(
                    [
                        "Regional Forecast Issued At: 05:00 AM.",
                        "Occasional rains 24 C 28 C.",
                        "Extended Weather Outlook.",
                        "Heavy Rainfall Warning No. 34.",
                        "RED WARNING LEVEL: Metro Manila, Bataan, Zambales, Pampanga.",
                        "ASSOCIATED HAZARD: FLOODING.",
                        "Unrelated extended forecast details " * 40,
                    ]
                ),
            )
        }
    )

    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main"), search=search, fetch=fetch),
    ).execute(intent("search_google", {"query": "current rainfall warning for Zambales"}))

    assert len(result.message) <= 1000
    assert "RED WARNING LEVEL" in result.message
    assert "Zambales" in result.message
    assert "Unrelated extended forecast details" not in result.message


def test_git_status_uses_configured_repository_and_fixed_adapter():
    repository = Path("C:/repo").resolve()
    git = FakeGitAdapter("## main")
    config = AssistantActionConfig(settings={"repositoryPath": str(repository)})
    result = build_action_registry(config, SimpleNamespace(git=git)).execute(intent("git_status"))

    assert result.handled is True
    assert result.message == "## main"
    assert git.repository == repository
