from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject unexpected fields so context/data mismatches are visible early."""

    model_config = ConfigDict(extra="forbid")


class GuestPreferences(StrictModel):
    dietary_preferences: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_vibe: list[str] = Field(default_factory=list)


class PropertyContext(StrictModel):
    name: str
    area: str
    latitude: float | None = None
    longitude: float | None = None
    check_in_time: time | None = None
    check_out_time: time | None = None


class ItineraryItemContext(StrictModel):
    item_id: str
    date: date
    start_time: time | None = None
    end_time: time | None = None
    title: str
    place_id: str | None = None
    area: str
    category: str
    setting: Literal["indoor", "outdoor", "mixed"]
    status: Literal["planned", "approved", "cancelled"] = "planned"


class TripContext(StrictModel):
    """Small, explicit context object passed from backend services to the agent."""

    trip_id: str
    booking_reference: str
    check_in: date
    check_out: date
    guest_count: int = Field(ge=1)
    property: PropertyContext
    preferences: GuestPreferences = Field(default_factory=GuestPreferences)
    itinerary: list[ItineraryItemContext] = Field(default_factory=list)
