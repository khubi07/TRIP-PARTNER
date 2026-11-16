import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.schemas.weather import WeatherDay, WeatherForecast

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherServiceError(RuntimeError):
    """A safe, user-facing weather lookup failure."""


class WeatherLocationNotFoundError(WeatherServiceError):
    """No matching Meghalaya location could be resolved."""


def _clean_area(area: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", "", area).strip()
    if not cleaned or len(cleaned) > 100:
        raise WeatherLocationNotFoundError("Enter a valid Meghalaya area name.")
    return cleaned


def _resolve_location(area: str, client: httpx.Client) -> dict[str, Any]:
    location_name = _clean_area(area)
    try:
        response = client.get(
            GEOCODING_URL,
            params={
                "name": f"{location_name}, Meghalaya",
                "countryCode": "IN",
                "count": 5,
                "language": "en",
                "format": "json",
            },
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise WeatherServiceError("Could not resolve the weather location right now.") from exc

    for result in results:
        admin1 = str(result.get("admin1", "")).casefold()
        country_code = str(result.get("country_code", "")).upper()
        if country_code == "IN" and (not admin1 or admin1 == "meghalaya"):
            return result
    raise WeatherLocationNotFoundError(
        f"I couldn't resolve '{location_name}' as a Meghalaya location. Try a nearby town."
    )


def _daily_value(daily: dict[str, Any], field: str, index: int) -> Any:
    values = daily.get(field, [])
    return values[index] if index < len(values) else None


class OpenMeteoWeatherService:
    """Fetch and normalize a short daily forecast from Open-Meteo."""

    def get_forecast(self, area: str, forecast_days: int = 7) -> WeatherForecast:
        if not 1 <= forecast_days <= 16:
            raise ValueError("forecast_days must be between 1 and 16")

        timeout = httpx.Timeout(10.0, connect=5.0)
        try:
            with httpx.Client(timeout=timeout) as client:
                location = _resolve_location(area, client)
                forecast_response = client.get(
                    FORECAST_URL,
                    params={
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                        "daily": ",".join(
                            [
                                "weather_code",
                                "temperature_2m_max",
                                "temperature_2m_min",
                                "precipitation_probability_max",
                                "precipitation_sum",
                            ]
                        ),
                        "forecast_days": forecast_days,
                        "timezone": "auto",
                    },
                )
                forecast_response.raise_for_status()
                payload = forecast_response.json()
        except httpx.TimeoutException as exc:
            raise WeatherServiceError("The weather service took too long to respond.") from exc
        except httpx.HTTPError as exc:
            raise WeatherServiceError("Could not fetch the forecast right now.") from exc
        except ValueError as exc:
            if isinstance(exc, WeatherServiceError):
                raise
            raise WeatherServiceError("The weather service returned invalid data.") from exc

        daily = payload.get("daily", {})
        days: list[WeatherDay] = []
        for index, forecast_date in enumerate(daily.get("time", [])):
            raw_code = _daily_value(daily, "weather_code", index)
            if raw_code is None:
                continue
            code = int(raw_code)
            days.append(
                WeatherDay(
                    date=forecast_date,
                    weather_code=code,
                    description=WEATHER_DESCRIPTIONS.get(code, "Conditions unavailable"),
                    precipitation_probability_max=_daily_value(
                        daily, "precipitation_probability_max", index
                    ),
                    precipitation_sum_mm=_daily_value(daily, "precipitation_sum", index),
                    temperature_max_c=_daily_value(daily, "temperature_2m_max", index),
                    temperature_min_c=_daily_value(daily, "temperature_2m_min", index),
                )
            )

        if not days:
            raise WeatherServiceError("The weather service returned no daily forecast data.")

        admin1 = location.get("admin1")
        country = location.get("country")
        label = ", ".join(
            part for part in [location.get("name"), admin1, country] if part
        )
        return WeatherForecast(
            requested_area=area,
            resolved_location=label,
            latitude=payload.get("latitude", location["latitude"]),
            longitude=payload.get("longitude", location["longitude"]),
            timezone=payload.get("timezone", location.get("timezone", "auto")),
            fetched_at=datetime.now(timezone.utc),
            forecast_days=days,
        )


weather_service = OpenMeteoWeatherService()
