from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.action_registry import build_action_registry
from app.modules.assistant.adapters.network import WeatherReport
from tests.support import intent


class FakeWeatherProvider:
    def __init__(self):
        self.location = None

    def get_weather(self, location: str):
        self.location = location
        return WeatherReport(location, "30", "clear")


class FakeUpdateProvider:
    def get_updates(self) -> str:
        return "No updates found."


def test_weather_action_uses_requested_location():
    weather = FakeWeatherProvider()
    registry = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(weather=weather, updates=FakeUpdateProvider()),
    )

    result = registry.execute(intent("get_weather", {"location": "Manila"}))

    assert result.handled is True
    assert result.message == "Manila: 30 C, clear."
    assert weather.location == "Manila"


def test_weather_uses_configured_location_and_updates_provider():
    weather = FakeWeatherProvider()
    config = AssistantActionConfig(settings={"weatherLocation": "Cebu, Philippines"})
    registry = build_action_registry(
        config,
        SimpleNamespace(weather=weather, updates=FakeUpdateProvider()),
    )

    weather_result = registry.execute(intent("get_weather"))
    updates_result = registry.execute(intent("get_updates"))

    assert weather_result.message == "Cebu, Philippines: 30 C, clear."
    assert updates_result.message == "No updates found."
