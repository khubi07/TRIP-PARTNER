from datetime import date, datetime
from typing import Literal

from app.schemas.trip_context import StrictModel


class WeatherDay(StrictModel):
    date: date
    weather_code: int
    description: str
    precipitation_probability_max: int | None = None
    precipitation_sum_mm: float | None = None
    temperature_max_c: float | None = None
    temperature_min_c: float | None = None


class WeatherForecast(StrictModel):
    requested_area: str
    resolved_location: str
    latitude: float
    longitude: float
    timezone: str
    fetched_at: datetime
    forecast_days: list[WeatherDay]
    provider: Literal["Open-Meteo"] = "Open-Meteo"
    source_url: str = "https://open-meteo.com/en/docs"
    attribution: str = "Weather data by Open-Meteo; location data based on GeoNames."
