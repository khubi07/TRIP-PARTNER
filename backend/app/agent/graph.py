from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agent.model import get_chat_model
from app.agent.schemas import AnswerDraft, RouteDecision, WeatherAnswerDraft
from app.schemas.search import SearchFilters
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
    weather: dict[str, Any]
    needs_refinement: bool
    fallback_message: str | None


ROUTER_PROMPT = """You route requests for tripPartner, a Meghalaya trip concierge.
Choose exactly one intent:
- recommendation: ask for a place, activity, food, or local suggestion
- itinerary: ask to plan or organize multiple trip activities
- weather: ask for weather or a weather-based change
- clarification: not enough information to safely choose another intent

Use the provided trip context. For recommendations, set retrieval_query to a short
keyword query suited to the local catalogue; use the booked property's area when
'near me' is implied. For weather, use the explicitly named area or the booked
property's area if the guest asks about their trip. For itinerary requests, make
retrieval_query broad enough for the local catalogue (for example: cave waterfall
village river). Use area, category, and setting only when supported. If key intent
or location is unclear, choose clarification and ask one concise question. Do not
invent places or claim to have checked live weather."""

ANSWER_PROMPT = """You are tripPartner, a careful Meghalaya trip concierge.
Use only the candidate records below for place-specific facts. Do not invent places,
prices, opening hours, travel times, availability, or weather. Personalize using the
trip context when relevant. For itinerary requests, arrange only supplied candidate
places into a practical high-level suggestion; do not claim route times or guarantee
feasibility. Ask for refinement if the evidence is insufficient. Return citations by
using candidate place IDs only. Keep the answer concise and useful."""

WEATHER_PROMPT = """You are tripPartner, a careful trip concierge. Answer from the supplied
Open-Meteo forecast only. Preserve the resolved location, local forecast dates,
precipitation probabilities, temperatures and conditions accurately. Do not invent
weather details or imply certainty beyond a forecast. If asked about an itinerary
change, describe the relevant weather and ask whether the guest wants alternatives;
this workflow does not modify an itinerary yet. Mention that the data is a forecast."""


def route_request(state: TripAssistantState) -> dict[str, Any]:
    context = state.get("trip_context", {})
    query = state.get("query", "")
    model = get_chat_model().with_structured_output(RouteDecision)
    decision = model.invoke(
        [
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(
                content=(
                    f"Trip context (JSON): {context}\n"
                    f"Guest request: {query}"
                )
            ),
        ]
    )
    decision_data = (
        decision
        if isinstance(decision, dict)
        else decision.model_dump(mode="json")
    )
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
        "answer": draft_data["message"],
        "citations": citations,
        "needs_refinement": False,
    }


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
