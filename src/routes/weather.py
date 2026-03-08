"""Weather API: GET /weather."""

from fastapi import APIRouter

from src.log_config import logger as log
from src.tools.weather import get_weather_dict

router = APIRouter(tags=["weather"])


@router.get("/weather")
async def weather(city: str | None = None):
    """Return current weather for the configured or given city."""
    log.info(f"Weather request city={city or 'default'}")
    return get_weather_dict(city=city)
