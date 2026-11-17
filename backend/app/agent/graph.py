from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agent.model import get_chat_model
from app.agent.schemas import AnswerDraft, WeatherAnswerDraft
from app.schemas.search import SearchFilters
from app.services.itinerary_validation import validate_itinerary_draft
from app.services.place_search import place_search
from app.services.weather import weather_service


class TripAssistantState(TypedDict, total=False):
    query: str
    trip_context: dict[str, Any]
    intent: str
    route_decision: dict[str, Any]
    candidates: list[dict[str, Any]]
    answer: str
    citations: list[dict[str, str]]
    itinerary: list[dict[str, Any]]
    weather: dict[str, Any]
    needs_refinement: bool
    fallback_message: str | None


ANSWER_PROMPT = """You are tripPartner, a careful Meghalaya trip concierge.
Use only the candidate records below for place-specific facts. Do not invent places,
prices, opening hours, travel times, availability, or weather. Personalize using the
trip context when relevant. For itinerary requests, populate itinerary_items using
candidate place IDs only, dates inside the booked trip, and optional non-overlapping
time blocks. Do not claim route times or guarantee feasibility. Keep message concise;
the application will render the validated itinerary and citations."""

WEATHER_PROMPT = """You are tripPartner, a careful trip concierge. Answer from the supplied
Open-Meteo forecast only. Preserve the resolved location, local forecast dates,
precipitation probabilities, temperatures and conditions accurately. Do not invent
weather details or imply certainty beyond a forecast. If asked about an itinerary
change, describe the relevant weather and ask whether the guest wants alternatives;
this workflow does not modify an itinerary yet. Mention that the data is a forecast."""


def route_request(state: TripAssistantState) -> dict[str, Any]:
    context = state.get("trip_context", {})
    query = state.get("query", "").strip()
    normalized = query.casefold()
    weather_terms = ("weather", "forecast", "rain", "raining", "temperature")
    itinerary_terms = ("itinerary", "plan", "schedule", "organize", "three-day", "3-day", "3 day")
    intent = (
        "weather" if any(term in normalized for term in weather_terms)
        else "itinerary" if any(term in normalized for term in itinerary_terms)
        else "clarification" if len(normalized.split()) < 3
        else "recommendation"
    )
    category = None
    if any(term in normalized for term in ("restaurant", "dinner", "food", "eat", "vegetarian", "jain")):
        category = "restaurant"
    elif any(term in normalized for term in ("cave", "caves")):
        category = "cave"
    elif any(term in normalized for term in ("waterfall", "falls")):
        category = "waterfall"
    elif any(term in normalized for term in ("village", "culture", "root bridge")):
        category = "village"
    elif any(term in normalized for term in ("river", "boating", "boat")):
        category = "river_activity"
    area = next((name for name in ("Sohra", "Cherrapunji", "Shillong", "Dawki", "Mawlynnong") if name.casefold() in normalized), None)
    if not area and ("near me" in normalized or "nearby" in normalized):
        area = context.get("property", {}).get("area")
    decision_data = {
        "intent": intent,
        "retrieval_query": query if intent != "itinerary" else "cave waterfall village river",
        "area": area,
        "weather_location": area,
        "category": category if intent == "recommendation" else None,
        "setting": "indoor" if any(term in normalized for term in ("indoors", "indoor")) else None,
        "clarification_question": "What would you like help with in Meghalaya?" if intent == "clarification" else "",
    }
    return {
        "intent": decision_data["intent"],
        "route_decision": decision_data,
    }


def choose_path(state: TripAssistantState) -> Literal["clarify", "search", "weather"]:
    intent = state.get("intent", "clarification")
    if intent == "clarification":
        return "clarify"
    if intent == "weather":
        return "weather"
    return "search"


def ask_clarification(state: TripAssistantState) -> dict[str, Any]:
    decision = state.get("route_decision", {})
    question = decision.get("clarification_question") or (
        "What area of Meghalaya or type of experience would you like help with?"
    )
    return {
        "answer": question,
        "citations": [],
        "needs_refinement": True,
        "fallback_message": None,
    }


def retrieve_places(state: TripAssistantState) -> dict[str, Any]:
    context = state.get("trip_context", {})
    decision = state.get("route_decision", {})
    intent = state.get("intent", "clarification")
    query_text = state.get("query", "")

    if intent == "itinerary":
        search_query = decision.get("retrieval_query") or "cave waterfall village river"
        filters = SearchFilters()
        top_k = 10
    else:
        search_query = decision.get("retrieval_query") or query_text
        area = decision.get("area")
        if not area and "near me" in query_text.casefold():
            area = context.get("property", {}).get("area")
        filters = SearchFilters(
            area=area,
            category=decision.get("category"),
            setting=decision.get("setting"),
        )
        top_k = 5

    result = place_search.search(search_query, filters=filters, top_k=top_k)
    candidates = [item.record.model_dump(mode="json") for item in result.results]
    return {
        "candidates": candidates,
        "needs_refinement": result.needs_refinement,
        "fallback_message": result.fallback_message,
    }


def draft_answer(state: TripAssistantState) -> dict[str, Any]:
    candidates = state.get("candidates", [])
    if not candidates:
        return {
            "answer": state.get("fallback_message")
            or "I couldn't find a reliable match. Could you refine your request?",
            "citations": [],
            "needs_refinement": True,
        }

    intent = state.get("intent", "clarification")
    query = state.get("query", "")
    context = state.get("trip_context", {})
    model = get_chat_model().with_structured_output(AnswerDraft)
    draft = model.invoke(
        [
            SystemMessage(content=ANSWER_PROMPT),
            HumanMessage(
                content=(
                    f"Intent: {intent}\n"
                    f"Guest request: {query}\n"
                    f"Trip context: {context}\n"
                    f"Candidate place records (JSON): {candidates}"
                )
            ),
        ]
    )
    draft_data = (
        draft
        if isinstance(draft, dict)
        else draft.model_dump(mode="json")
    )

    records_by_id = {record["id"]: record for record in candidates}
    itinerary_items: list[dict[str, Any]] = []
    answer_text = draft_data["message"]
    if intent == "itinerary":
        itinerary_items = draft_data.get("itinerary_items", [])
        validation_errors = validate_itinerary_draft(
            itinerary_items,
            context,
            records_by_id,
        )
        if not itinerary_items:
            validation_errors.append("No itinerary stops were returned.")
        if validation_errors:
            return {
                "answer": (
                    "I couldn't validate the proposed stops against the local places "
                    "and your trip dates, so I haven't returned an itinerary. Please "
                    "try again with the number of days or area you want to explore."
                ),
                "citations": [],
                "itinerary": [],
                "needs_refinement": True,
                "fallback_message": "; ".join(validation_errors),
            }
        itinerary_items = [
            {
                **item,
                "title": records_by_id[item["place_id"]]["name"],
                "area": records_by_id[item["place_id"]]["area"],
            }
            for item in itinerary_items
        ]
        valid_ids = list(dict.fromkeys(item["place_id"] for item in itinerary_items))
        answer_text = _format_itinerary(itinerary_items, records_by_id)
    else:
        valid_ids = list(dict.fromkeys(
            place_id
            for place_id in draft_data["cited_place_ids"]
            if place_id in records_by_id
        ))
    if not valid_ids:
        valid_ids = list(records_by_id)
    citations = [
        {
            "source_id": place_id,
            "source_type": "place",
            "title": records_by_id[place_id]["name"],
            "url": str(records_by_id[place_id]["source"]["url"]),
        }
        for place_id in valid_ids
    ]
    return {
        "answer": answer_text,
        "citations": citations,
        "itinerary": itinerary_items,
        "needs_refinement": False,
    }


def _format_itinerary(
    items: list[dict[str, Any]],
    records_by_id: dict[str, dict[str, Any]],
) -> str:
    """Render only validated place records and proposed schedule blocks."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item["date"], []).append(item)
    lines = ["Here’s a draft itinerary using places from the local guide:"]
    for day_index, (day, day_items) in enumerate(sorted(grouped.items()), start=1):
        lines.extend(["", f"Day {day_index} · {day}"])
        for item in sorted(day_items, key=lambda entry: entry.get("start_time") or "00:00"):
            record = records_by_id[item["place_id"]]
            start = item.get("start_time")
            end = item.get("end_time")
            time_range = f"{start[:5]}–{end[:5]} · " if start and end else ""
            lines.append(f"{time_range}{record['name']} — {record['area']}")
    lines.extend(["", "Times are suggested blocks; confirm opening hours and transport locally."])
    return "\n".join(lines)


def lookup_weather(state: TripAssistantState) -> dict[str, Any]:
    context = state.get("trip_context", {})
    decision = state.get("route_decision", {})
    area = (
        decision.get("weather_location")
        or decision.get("area")
        or context.get("property", {}).get("area")
    )
    if not area:
        return {
            "answer": "Which town or area in Meghalaya should I check?",
            "citations": [],
            "needs_refinement": True,
        }
    forecast = weather_service.get_forecast(area, forecast_days=7)
    return {"weather": forecast.model_dump(mode="json")}


def draft_weather_answer(state: TripAssistantState) -> dict[str, Any]:
    forecast = state.get("weather", {})
    query = state.get("query", "")
    context = state.get("trip_context", {})
    model = get_chat_model().with_structured_output(WeatherAnswerDraft)
    draft = model.invoke(
        [
            SystemMessage(content=WEATHER_PROMPT),
            HumanMessage(
                content=(
                    f"Guest request: {query}\n"
                    f"Trip context: {context}\n"
                    f"Normalized forecast JSON: {forecast}"
                )
            ),
        ]
    )
    draft_data = (
        draft
        if isinstance(draft, dict)
        else draft.model_dump(mode="json")
    )
    return {
        "answer": draft_data["message"],
        "citations": [
            {
                "source_id": "open-meteo-forecast",
                "source_type": "weather",
                "title": (
                    "Open-Meteo forecast for "
                    f"{forecast.get('resolved_location', 'the requested area')}"
                ),
                "url": forecast.get("source_url", "https://open-meteo.com/en/docs"),
            }
        ],
        "needs_refinement": False,
    }


def build_assistant_graph():
    graph = StateGraph(TripAssistantState)
    graph.add_node("route_request", route_request)
    graph.add_node("ask_clarification", ask_clarification)
    graph.add_node("retrieve_places", retrieve_places)
    graph.add_node("draft_answer", draft_answer)
    graph.add_node("lookup_weather", lookup_weather)
    graph.add_node("draft_weather_answer", draft_weather_answer)

    graph.add_edge(START, "route_request")
    graph.add_conditional_edges(
        "route_request",
        choose_path,
        {
            "clarify": "ask_clarification",
            "search": "retrieve_places",
            "weather": "lookup_weather",
        },
    )
    graph.add_edge("retrieve_places", "draft_answer")
    graph.add_edge("lookup_weather", "draft_weather_answer")
    graph.add_edge("ask_clarification", END)
    graph.add_edge("draft_answer", END)
    graph.add_edge("draft_weather_answer", END)
    return graph.compile()


assistant_graph = build_assistant_graph()
