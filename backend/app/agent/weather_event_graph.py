from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import Field

from app.agent.model import get_chat_model
from app.schemas.search import SearchFilters
from app.schemas.trip_context import StrictModel
from app.services.place_search import place_search

MIN_RAIN_PROBABILITY = 60
MIN_PROBABILITY_INCREASE = 20
ACTIVE_ITEM_STATUSES = {"planned", "approved"}


class WeatherEventDraft(StrictModel):
    message: str = Field(min_length=1, max_length=2000)


class WeatherEventState(TypedDict, total=False):
    event: dict[str, Any]
    trip_context: dict[str, Any]
    impact_detected: bool
    affected_items: list[dict[str, Any]]
    candidates: list[dict[str, Any]]
    status: str
    message: str
    precipitation_change: int
    suggested_alternative: dict[str, Any] | None
    citations: list[dict[str, str]]
    requires_guest_approval: bool
    llm_used: bool


WEATHER_EVENT_PROMPT = """You are tripPartner drafting a proactive weather notice.
Use only the supplied event, affected itinerary item, and alternative record. State
that the precipitation probability increased and explain which outdoor plan it may
affect. Suggest the exact alternative, note its setting accurately, and ask the guest
to approve before any itinerary change. Do not claim the alternative is weather-proof,
open, available, or already booked. Do not invent travel times or extra places."""


def evaluate_weather_impact(state: WeatherEventState) -> dict[str, Any]:
    event = state.get("event", {})
    context = state.get("trip_context", {})
    previous_probability = int(event.get("previous_precipitation_probability", 0))
    current_probability = int(event.get("current_precipitation_probability", 0))
    probability_change = current_probability - previous_probability
    forecast_date = str(event.get("forecast_date", ""))

    outdoor_items = [
        item
        for item in context.get("itinerary", [])
        if str(item.get("date", "")) == forecast_date
        and item.get("setting") == "outdoor"
        and item.get("status") in ACTIVE_ITEM_STATUSES
    ]
    threshold_met = (
        current_probability >= MIN_RAIN_PROBABILITY
        and probability_change >= MIN_PROBABILITY_INCREASE
    )
    impact_detected = threshold_met and bool(outdoor_items)

    if not threshold_met:
        message = (
            f"Rain probability changed from {previous_probability}% to "
            f"{current_probability}% ({probability_change:+d} points). The demo "
            "trigger requires at least 60% probability and a 20-point increase; "
            "no itinerary item was changed."
        )
    elif not outdoor_items:
        message = (
            f"The rain trigger was met for {forecast_date}, but there is no active "
            "outdoor itinerary item on that date. No AI call was needed and no "
            "itinerary item was changed."
        )
    else:
        message = "Weather may affect an outdoor itinerary item; checking alternatives."

    return {
        "impact_detected": impact_detected,
        "affected_items": outdoor_items if impact_detected else [],
        "status": "pending" if impact_detected else "no_action",
        "message": message,
        "precipitation_change": probability_change,
        "requires_guest_approval": False,
        "llm_used": False,
        "citations": [],
    }


def choose_event_path(state: WeatherEventState) -> Literal["search", "finish"]:
    return "search" if state.get("impact_detected", False) else "finish"


def find_indoor_alternatives(state: WeatherEventState) -> dict[str, Any]:
    event = state.get("event", {})
    context = state.get("trip_context", {})
    area = event.get("area") or context.get("property", {}).get("area")
    event_date = str(event.get("forecast_date", ""))
    scheduled_ids = {
        item.get("place_id")
        for item in context.get("itinerary", [])
        if str(item.get("date", "")) == event_date and item.get("place_id")
    }

    result = place_search.search(
        "cave fossils rainy day",
        filters=SearchFilters(area=area, category="cave"),
        top_k=5,
    )
    candidates = [
        item.record.model_dump(mode="json")
        for item in result.results
        if item.record.id not in scheduled_ids
        and item.record.setting in {"indoor", "mixed"}
    ]
    if not candidates:
        return {
            "status": "no_alternative_found",
            "candidates": [],
            "message": (
                f"Rain risk increased for {event_date}, affecting an outdoor "
                "activity. The local dataset has no unscheduled cave alternative "
                f"near {area or 'the trip area'}; no plan was changed."
            ),
            "requires_guest_approval": False,
            "llm_used": False,
        }
    return {"candidates": candidates}


def choose_draft_path(state: WeatherEventState) -> Literal["draft", "finish"]:
    return "draft" if state.get("candidates", []) else "finish"


def draft_weather_suggestion(state: WeatherEventState) -> dict[str, Any]:
    event = state.get("event", {})
    affected_items = state.get("affected_items", [])
    candidates = state.get("candidates", [])
    alternative = candidates[0]
    model = get_chat_model().with_structured_output(WeatherEventDraft)
    draft = model.invoke(
        [
            SystemMessage(content=WEATHER_EVENT_PROMPT),
            HumanMessage(
                content=(
                    f"Weather-change event: {event}\n"
                    f"Affected itinerary items: {affected_items}\n"
                    f"Retrieved alternative records: {candidates}"
                )
            ),
        ]
    )
    draft_data = (
        draft
        if isinstance(draft, dict)
        else draft.model_dump(mode="json")
    )
    message = draft_data.get("message") or (
        "Rain risk increased for an outdoor itinerary item. An alternative is "
        f"{alternative.get('name', 'a nearby cave')}; please approve before the plan changes."
    )
    if event.get("event_source", "simulated") == "simulated":
        message += " (This is a simulated weather-change event.)"

    return {
        "status": "suggestion_created",
        "message": message,
        "suggested_alternative": {
            "place_id": alternative.get("id", ""),
            "title": alternative.get("name", "Local cave alternative"),
            "area": alternative.get("area", ""),
            "summary": alternative.get("summary", ""),
            "setting": alternative.get("setting", "mixed"),
        },
        "citations": [
            {
                "source_id": alternative.get("id", ""),
                "source_type": "place",
                "title": alternative.get("name", "Local cave alternative"),
                "url": str(alternative.get("source", {}).get("url", "")),
            }
        ],
        "requires_guest_approval": True,
        "llm_used": True,
    }


def build_weather_event_graph():
    graph = StateGraph(WeatherEventState)
    graph.add_node("evaluate_impact", evaluate_weather_impact)
    graph.add_node("find_alternatives", find_indoor_alternatives)
    graph.add_node("draft_suggestion", draft_weather_suggestion)

    graph.add_edge(START, "evaluate_impact")
    graph.add_conditional_edges(
        "evaluate_impact",
        choose_event_path,
        {"search": "find_alternatives", "finish": END},
    )
    graph.add_conditional_edges(
        "find_alternatives",
        choose_draft_path,
        {"draft": "draft_suggestion", "finish": END},
    )
    graph.add_edge("draft_suggestion", END)
    return graph.compile()


weather_event_graph = build_weather_event_graph()
