import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query

from app.agent.graph import assistant_graph
from app.agent.model import MissingGeminiKeyError
from app.schemas.assistant import ChatRequest, ChatResponse
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


def load_demo_trip_context() -> TripContext:
    raw_context = json.loads((DATA_DIR / "demo_trip_context.json").read_text(encoding="utf-8"))
    return TripContext.model_validate(raw_context)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok"}


@app.get("/demo/trip-context", response_model=TripContext, tags=["demo"])
def get_demo_trip_context() -> TripContext:
    """Load and validate fictional booking and itinerary context."""
    return load_demo_trip_context()


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


@app.post("/assistant/chat", response_model=ChatResponse, tags=["assistant"])
def chat(request: ChatRequest) -> ChatResponse:
    """Route a guest message through the LangGraph assistant workflow."""
    context = load_demo_trip_context().model_dump(mode="json")
    try:
        state = assistant_graph.invoke(
            {"query": request.message, "trip_context": context}
        )
    except MissingGeminiKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Keep provider/network details out of API responses and logs by default.
        raise HTTPException(
            status_code=502,
            detail="The AI provider request failed. Please retry shortly.",
        ) from exc

    return ChatResponse(
        intent=state.get("intent", "clarification"),
        answer=state.get("answer", "I couldn't complete that request."),
        citations=state.get("citations", []),
        needs_refinement=state.get("needs_refinement", False),
        fallback_message=state.get("fallback_message"),
    )
