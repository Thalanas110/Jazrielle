from app.modules.assistant.adapters import network
from app.modules.assistant.adapters.network import GoogleSearchProvider, SearchResult


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del exc_type, exc_value, traceback

    def read(self):
        return self.content


def test_google_search_parses_safe_result_titles_snippets_and_links(monkeypatch):
    html = b"""
    <a href="/url?q=https%3A%2F%2Fpagasa.dost.gov.ph%2F&amp;sa=U"><h3>PAGASA</h3></a>
    <div class="VwiC3b">Rainfall warning information.</div>
    <a href="javascript:alert(1)"><h3>Unsafe result</h3></a>
    <div class="VwiC3b">Ignore this result.</div>
    """
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(html)

    monkeypatch.setattr(network, "urlopen", fake_urlopen)

    results = GoogleSearchProvider().search("color coded rainfall warning")

    assert results == [
        SearchResult(
            "PAGASA",
            "https://pagasa.dost.gov.ph/",
            "Rainfall warning information.",
        )
    ]
    assert captured["url"].startswith("https://www.google.com/search?")
    assert "q=color+coded+rainfall+warning" in captured["url"]
    assert captured["timeout"] == 5
