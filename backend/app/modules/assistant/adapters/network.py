import json
import subprocess
from dataclasses import dataclass
from urllib.parse import quote
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
