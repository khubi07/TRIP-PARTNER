import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Query

from app.schemas.place import PlaceRecord
from app.schemas.search import PlaceSearchResponse, SearchFilters
from app.schemas.trip_context import TripContext
from app.services.place_search import place_search

app = FastAPI(
    title="tripPartner API",
    description="Context-aware AI trip concierge for Meghalaya.",
    version="0.1.0",
)

DATA_DIR = Path(__file__).parent / "data"


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok"}


@app.get("/demo/trip-context", response_model=TripContext, tags=["demo"])
def get_demo_trip_context() -> TripContext:
    """Load and validate fictional booking and itinerary context."""
    raw_context = json.loads((DATA_DIR / "demo_trip_context.json").read_text(encoding="utf-8"))
    return TripContext.model_validate(raw_context)


@app.get("/places", response_model=list[PlaceRecord], tags=["knowledge"])
def list_places() -> list[PlaceRecord]:
    """Return all source-attributed local recommendations."""
    raw_places = json.loads((DATA_DIR / "places.json").read_text(encoding="utf-8"))
    return [PlaceRecord.model_validate(place) for place in raw_places]


@app.get("/recommendations/search", response_model=PlaceSearchResponse, tags=["knowledge"])
def search_recommendations(
    q: Annotated[str, Query(min_length=1, max_length=300)],
    area: Annotated[str | None, Query(max_length=100)] = None,
    category: Literal["cave", "waterfall", "village", "river_activity"] | None = None,
    setting: Literal["indoor", "outdoor", "mixed"] | None = None,
    top_k: Annotated[int, Query(ge=1, le=10)] = 5,
) -> PlaceSearchResponse:
    """Search local places using BM25 plus optional structured filters."""
    return place_search.search(
        q,
        filters=SearchFilters(area=area, category=category, setting=setting),
        top_k=top_k,
    )
