from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.assistant import Citation
from app.schemas.trip_context import StrictModel


class WeatherChangeEvent(StrictModel):
    """Forecast-change event emitted by a monitor or simulated in the demo."""

    trip_id: str
    forecast_date: date
    previous_precipitation_probability: int = Field(ge=0, le=100)
    current_precipitation_probability: int = Field(ge=0, le=100)
    area: str | None = Field(default=None, max_length=100)
    event_source: Literal["simulated", "open_meteo"] = "simulated"


class WeatherAlternative(StrictModel):
    place_id: str
    title: str
    area: str
    summary: str
    setting: Literal["indoor", "outdoor", "mixed"]


class WeatherEventResponse(StrictModel):
    trip_id: str
    forecast_date: date
    event_source: Literal["simulated", "open_meteo"]
    status: Literal["no_action", "no_alternative_found", "suggestion_created"]
    precipitation_change: int
    affected_item_ids: list[str] = Field(default_factory=list)
    message: str
    suggested_alternative: WeatherAlternative | None = None
    citations: list[Citation] = Field(default_factory=list)
    requires_guest_approval: bool = False
    llm_used: bool = False
