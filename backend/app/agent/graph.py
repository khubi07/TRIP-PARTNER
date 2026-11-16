from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.agent.model import get_chat_model
from app.agent.schemas import AnswerDraft, RouteDecision
from app.schemas.search import SearchFilters
from app.services.place_search import place_search


class TripAssistantState(TypedDict, total=False):
    query: str
    trip_context: dict[str, Any]
    intent: str
    route_decision: dict[str, Any]
    candidates: list[dict[str, Any]]
    candidate_ids: list[str]
    answer: str
    citations: list[dict[str, str]]
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
"near me" is implied. For itinerary requests, search_query should be broad enough
for the local catalogue (for example: cave waterfall village river). Use area,
category, and setting only when supported by the request/context. If key intent or
location is unclear, choose clarification and ask one concise question. Do not
invent places or claim to have checked live weather."""

ANSWER_PROMPT = """You are tripPartner, a careful Meghalaya trip concierge.
Use only the candidate records below for place-specific facts. Do not invent places,
prices, opening hours, travel times, availability, or weather. Personalize using the
trip context when relevant. For itinerary requests, arrange only supplied candidate
places into a practical high-level suggestion; do not claim route times or guarantee
feasibility. Ask for refinement if the evidence is insufficient. Return citations by
using candidate place IDs only. Keep the answer concise and useful."""


def route_request(state: TripAssistantState) -> dict[str, Any]:
    context = state.get("trip_context", {})
    model = get_chat_model().with_structured_output(RouteDecision)
    decision = RouteDecision.model_validate(model.invoke(
        [
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(
                content=(
                    f"Trip context (JSON): {context}\n"
                    f"Guest request: {state.get('query', '')}"
                )
            ),
        ]
    ))
    return {
        "intent": decision.intent,
        "route_decision": decision.model_dump(mode="json"),
    }


def choose_path(state: TripAssistantState) -> Literal["clarify", "search", "weather_pending"]:
    intent = state.get("intent", "clarification")
    if intent == "clarification":
        return "clarify"
    if intent == "weather":
        return "weather_pending"
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


def weather_pending(state: TripAssistantState) -> dict[str, Any]:
    return {
        "answer": (
            "I understand you’re asking about weather. The live weather tool is the "
            "next integration step; I haven’t checked a forecast yet."
        ),
        "citations": [],
        "needs_refinement": True,
        "fallback_message": "Live weather lookup is not connected yet.",
    }


def retrieve_places(state: TripAssistantState) -> dict[str, Any]:
    context = state.get("trip_context", {})
    decision = state.get("route_decision", {})
    if state.get("intent") == "itinerary":
        query = decision.get("retrieval_query") or "cave waterfall village river"
        filters = SearchFilters()
        top_k = 10
    else:
        query = decision.get("retrieval_query") or state.get("query", "")
        area = decision.get("area")
        if not area and "near me" in state.get("query", "").casefold():
            area = context.get("property", {}).get("area")
        filters = SearchFilters(
            area=area,
            category=decision.get("category"),
            setting=decision.get("setting"),
        )
        top_k = 5

    result = place_search.search(query, filters=filters, top_k=top_k)
    candidates = [item.record.model_dump(mode="json") for item in result.results]
    return {
        "candidates": candidates,
        "candidate_ids": [item["id"] for item in candidates],
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

    model = get_chat_model().with_structured_output(AnswerDraft)
    draft = AnswerDraft.model_validate(model.invoke(
        [
            SystemMessage(content=ANSWER_PROMPT),
            HumanMessage(
                content=(
                    f"Intent: {state.get('intent', 'clarification')}\n"
                    f"Guest request: {state.get('query', '')}\n"
                    f"Trip context: {state.get('trip_context', {})}\n"
                    f"Candidate place records (JSON): {candidates}"
                )
            ),
        ]
    ))

    records_by_id = {record["id"]: record for record in candidates}
    valid_ids = list(dict.fromkeys(
        place_id for place_id in draft.cited_place_ids if place_id in records_by_id
    ))
    if not valid_ids:
        valid_ids = list(records_by_id)
    citations = [
        {
            "place_id": place_id,
            "title": records_by_id[place_id]["name"],
            "url": str(records_by_id[place_id]["source"]["url"]),
        }
        for place_id in valid_ids
    ]
    return {
        "answer": draft.message,
        "citations": citations,
        "needs_refinement": False,
    }


def build_assistant_graph():
    graph = StateGraph(TripAssistantState)
    graph.add_node("route_request", route_request)
    graph.add_node("ask_clarification", ask_clarification)
    graph.add_node("weather_pending", weather_pending)
    graph.add_node("retrieve_places", retrieve_places)
    graph.add_node("draft_answer", draft_answer)

    graph.add_edge(START, "route_request")
    graph.add_conditional_edges(
        "route_request",
        choose_path,
        {
            "clarify": "ask_clarification",
            "search": "retrieve_places",
            "weather_pending": "weather_pending",
        },
    )
    graph.add_edge("retrieve_places", "draft_answer")
    graph.add_edge("ask_clarification", END)
    graph.add_edge("weather_pending", END)
    graph.add_edge("draft_answer", END)
    return graph.compile()


assistant_graph = build_assistant_graph()
