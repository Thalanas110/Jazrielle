import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from typing import Any, Protocol


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


@dataclass(frozen=True)
class FetchedPage:
    title: str
    url: str
    text: str


class SearchProvider(Protocol):
    def search(self, query: str) -> list[SearchResult]: ...


class FetchProvider(Protocol):
    def fetch(self, urls: list[str], purpose: str) -> dict[str, FetchedPage]: ...


class SearchNotConfiguredError(RuntimeError):
    """Raised when server-side web search has no TinyFish API key."""


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


class TinyFishSearchProvider:
    endpoint = "https://api.search.tinyfish.ai"

    def __init__(
        self,
        api_key: str | None,
        *,
        location: str = "PH",
        language: str = "en",
        timeout: int = 15,
    ):
        self._api_key = api_key.strip() if isinstance(api_key, str) else None
        self._location = location
        self._language = language
        self._timeout = timeout

    def search(self, query: str) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []
        request = Request(
            f"{self.endpoint}?"
            + urlencode(
                {
                    "query": query,
                    "purpose": f"Find the current answer to: {query}",
                    "location": self._location,
                    "language": self._language,
                }
            ),
            headers=self._headers(),
        )
        payload = _read_json(request, self._timeout)
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("TinyFish Search returned an invalid results payload.")
        results: list[SearchResult] = []
        for raw_result in raw_results:
            if not isinstance(raw_result, Mapping):
                continue
            url = _safe_web_url(raw_result.get("url"))
            title = raw_result.get("title")
            snippet = raw_result.get("snippet")
            if url is None or not isinstance(title, str) or not title.strip():
                continue
            results.append(
                SearchResult(
                    title=title.strip(),
                    url=url,
                    snippet=snippet.strip() if isinstance(snippet, str) else "",
                )
            )
        return results

    def _headers(self) -> dict[str, str]:
        return _tinyfish_headers(self._api_key)


class TinyFishFetchProvider:
    endpoint = "https://api.fetch.tinyfish.ai"

    def __init__(self, api_key: str | None, *, timeout: int = 45):
        self._api_key = api_key.strip() if isinstance(api_key, str) else None
        self._timeout = timeout

    def fetch(self, urls: list[str], purpose: str) -> dict[str, FetchedPage]:
        safe_urls = []
        for value in urls[:3]:
            url = _safe_web_url(value)
            if url is not None and url not in safe_urls:
                safe_urls.append(url)
        if not safe_urls:
            return {}
        request = Request(
            self.endpoint,
            data=json.dumps(
                {
                    "urls": safe_urls,
                    "format": "markdown",
                    "ttl": 0,
                    "purpose": purpose.strip()[:2000],
                }
            ).encode("utf-8"),
            headers={**_tinyfish_headers(self._api_key), "Content-Type": "application/json"},
            method="POST",
        )
        payload = _read_json(request, self._timeout)
        raw_pages = payload.get("results", [])
        if not isinstance(raw_pages, list):
            raise ValueError("TinyFish Fetch returned an invalid results payload.")
        pages: dict[str, FetchedPage] = {}
        for raw_page in raw_pages:
            if not isinstance(raw_page, Mapping):
                continue
            url = _safe_web_url(raw_page.get("url"))
            title = raw_page.get("title")
            text = raw_page.get("text")
            if url not in safe_urls or not isinstance(text, str) or not text.strip():
                continue
            pages[url] = FetchedPage(
                title=title.strip() if isinstance(title, str) else "",
                url=url,
                text=text.strip(),
            )
        return pages


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


def _tinyfish_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        raise SearchNotConfiguredError(
            "Set TINYFISH_API_KEY in backend/.env to enable web search."
        )
    return {"X-API-Key": api_key, "Accept": "application/json"}


def _read_json(request: Request, timeout: int) -> dict[str, Any]:
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("TinyFish returned a non-object JSON payload.")
    return payload


def _safe_web_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc or parsed.username or parsed.password:
        return None
    return candidate
