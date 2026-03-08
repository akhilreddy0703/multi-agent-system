"""Mock weather tool for the configured city. Swappable for OpenWeatherMap later."""

from src.config import settings


def get_weather(city: str | None = None) -> str:
    """Return current weather for the given city, or the configured default city.
    Use this to answer questions about weather."""
    target = (city or "").strip() or settings.weather_city
    return (
        f"Weather in {target}: 72°F (22°C), partly cloudy. "
        "Humidity 65%, wind 10 mph NE. (Mock data)"
    )


def get_weather_dict(city: str | None = None) -> dict:
    """Return current weather as a dict for REST API."""
    target = (city or "").strip() or settings.weather_city
    return {
        "city": target,
        "temperature_f": 72,
        "temperature_c": 22,
        "condition": "partly cloudy",
        "humidity_percent": 65,
        "wind": "10 mph NE",
        "source": "mock",
    }
