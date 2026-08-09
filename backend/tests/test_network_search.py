import json
from urllib.parse import parse_qs, urlparse

import pytest

from app.modules.assistant.adapters import network
from app.modules.assistant.adapters.network import (
    FetchedPage,
    SearchNotConfiguredError,
    SearchResult,
    TinyFishFetchProvider,
    TinyFishSearchProvider,
)


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback

    def read(self):
        return self.content


def test_tinyfish_search_returns_structured_results(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            b'{"results":[{"title":"PAGASA","url":"https://pagasa.dost.gov.ph/","snippet":"Rainfall warning information."}]}'
        )

    monkeypatch.setattr(network, "urlopen", fake_urlopen)

    results = TinyFishSearchProvider("secret", location="PH", language="en").search(
        "color coded rainfall warning"
    )

    assert results == [
        SearchResult(
            "PAGASA",
            "https://pagasa.dost.gov.ph/",
            "Rainfall warning information.",
        )
    ]
    request = captured["request"]
    query = parse_qs(urlparse(request.full_url).query)
    assert request.full_url.startswith("https://api.search.tinyfish.ai?")
    assert query["query"] == ["color coded rainfall warning"]
    assert query["location"] == ["PH"]
    assert query["language"] == ["en"]
    assert request.get_header("X-api-key") == "secret"
    assert captured["timeout"] == 15


def test_tinyfish_fetch_returns_page_content_and_requests_fresh_markdown(monkeypatch):
    captured = {}
    url = "https://pagasa.dost.gov.ph/"

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            json.dumps(
                {
                    "results": [
                        {
                            "url": url,
                            "final_url": url,
                            "title": "PAGASA",
                            "text": "Current rainfall warning information.",
                        }
                    ],
                    "errors": [],
                }
            ).encode()
        )

    monkeypatch.setattr(network, "urlopen", fake_urlopen)

    pages = TinyFishFetchProvider("secret").fetch([url], "Check the current rainfall warning.")

    assert pages == {
        url: FetchedPage("PAGASA", url, "Current rainfall warning information.")
    }
    request = captured["request"]
    payload = json.loads(request.data)
    assert request.full_url == "https://api.fetch.tinyfish.ai"
    assert request.get_method() == "POST"
    assert request.get_header("X-api-key") == "secret"
    assert payload == {
        "urls": [url],
        "format": "markdown",
        "ttl": 0,
        "purpose": "Check the current rainfall warning.",
    }
    assert captured["timeout"] == 45


def test_tinyfish_search_requires_an_api_key():
    with pytest.raises(SearchNotConfiguredError):
        TinyFishSearchProvider(None).search("rainfall warning")
