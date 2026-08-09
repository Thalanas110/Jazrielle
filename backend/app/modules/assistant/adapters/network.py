import json
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen
from typing import Protocol


@dataclass(frozen=True)
class WeatherReport:
    location: str
    temperature_c: str
    description: str


class WeatherProvider(Protocol):
    def get_weather(self, location: str) -> WeatherReport: ...


class UpdateProvider(Protocol):
    def get_updates(self) -> str: ...


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider(Protocol):
    def search(self, query: str) -> list[SearchResult]: ...


class WttrWeatherProvider:
    def get_weather(self, location: str) -> WeatherReport:
        request = Request(
            f"https://wttr.in/{quote(location)}?format=j1",
            headers={"User-Agent": "Jazrielle/1.0"},
        )
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        current = payload["current_condition"][0]
        return WeatherReport(
            location=location,
            temperature_c=str(current["temp_C"]),
            description=str(current["weatherDesc"][0]["value"]),
        )


class _GoogleResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._anchor_hrefs: list[str | None] = []
        self._current_title: list[str] | None = None
        self._current_title_url: str | None = None
        self._titles: list[tuple[str, str | None]] = []
        self._current_snippet: list[str] | None = None
        self._snippet_depth = 0
        self._snippets: list[str] = []

    @property
    def results(self) -> list[SearchResult]:
        results: list[SearchResult] = []
        for index, (raw_title, raw_url) in enumerate(self._titles):
            url = _normalize_search_result_url(raw_url)
            if url is None:
                continue
            snippet = self._snippets[index] if index < len(self._snippets) else ""
            results.append(SearchResult(raw_title, url, snippet))
        return results

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self._anchor_hrefs.append(attributes.get("href"))
        if tag == "h3":
            self._current_title = []
            self._current_title_url = self._anchor_hrefs[-1] if self._anchor_hrefs else None
        classes = set((attributes.get("class") or "").split())
        if "VwiC3b" in classes and self._current_snippet is None:
            self._current_snippet = []
            self._snippet_depth = 1
        elif self._current_snippet is not None:
            self._snippet_depth += 1

    def handle_data(self, data: str) -> None:
        if self._current_title is not None:
            self._current_title.append(data)
        if self._current_snippet is not None:
            self._current_snippet.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._current_snippet is not None:
            self._snippet_depth -= 1
            if self._snippet_depth == 0:
                snippet = " ".join("".join(self._current_snippet).split())
                self._snippets.append(snippet)
                self._current_snippet = None
        if tag == "h3" and self._current_title is not None:
            title = " ".join("".join(self._current_title).split())
            self._titles.append((title, self._current_title_url))
            self._current_title = None
            self._current_title_url = None
        if tag == "a" and self._anchor_hrefs:
            self._anchor_hrefs.pop()


def _normalize_search_result_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    parsed = urlparse(raw_url)
    if parsed.path == "/url":
        raw_url = parse_qs(parsed.query).get("q", [""])[0]
        parsed = urlparse(raw_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc or parsed.username or parsed.password:
        return None
    return parsed.geturl()


class GoogleSearchProvider:
    def search(self, query: str) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []
        search_url = "https://www.google.com/search?" + urlencode(
            {"q": query, "num": 5, "hl": "en"}
        )
        request = Request(search_url, headers={"User-Agent": "Jazrielle/1.0"})
        with urlopen(request, timeout=5) as response:
            parser = _GoogleResultParser()
            parser.feed(response.read().decode("utf-8", errors="ignore"))
        return parser.results


class WingetUpdateProvider:
    def get_updates(self) -> str:
        result = subprocess.run(
            ["winget", "upgrade", "--include-unknown"],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout or result.stderr).strip()
        return output or "No update information was returned."
