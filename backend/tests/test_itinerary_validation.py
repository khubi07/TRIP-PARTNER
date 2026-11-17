from app.agent import graph as assistant_graph_module
from app.agent.graph import draft_answer
from app.schemas.assistant import ChatResponse
from app.services.itinerary_validation import validate_itinerary_draft
from app.services.place_search import place_search


def _records_by_id(*place_ids):
    return {
        record.id: record.model_dump(mode="json")
        for record in place_search.records
        if record.id in place_ids
    }


def test_valid_itinerary_uses_only_retrieved_places_and_trip_dates(monkeypatch, demo_trip_context):
    candidates = _records_by_id("mawsmai-cave", "nohkalikai-falls")
    monkeypatch.setattr(
        assistant_graph_module,
        "get_chat_model",
        lambda: _FakeChatModel(
            {
                "message": "A flexible two-stop day.",
                "cited_place_ids": [],
                "itinerary_items": [
                    {"date": "2027-01-16", "place_id": "mawsmai-cave", "start_time": "09:00:00Z", "end_time": "11:00:00Z"},
                    {"date": "2027-01-16", "place_id": "nohkalikai-falls", "start_time": "11:00:00Z", "end_time": "13:00:00Z"},
                ],
            }
        ),
    )

    result = draft_answer(
        {
            "intent": "itinerary",
            "query": "Plan a day around Sohra",
            "trip_context": demo_trip_context,
            "candidates": list(candidates.values()),
        }
    )

    assert result["needs_refinement"] is False
    assert {item["place_id"] for item in result["itinerary"]} == set(candidates)
    assert {citation["source_id"] for citation in result["citations"]} == set(candidates)
    assert "Mawsmai Cave" in result["answer"]
    assert "Nohkalikai Falls" in result["answer"]
    response = ChatResponse(intent="itinerary", **result)
    assert len(response.itinerary) == 2
    assert response.itinerary[0].title in {"Mawsmai Cave", "Nohkalikai Falls"}


def test_invalid_itinerary_is_rejected_without_citations(monkeypatch, demo_trip_context):
    candidates = _records_by_id("mawsmai-cave")
    monkeypatch.setattr(
        assistant_graph_module,
        "get_chat_model",
        lambda: _FakeChatModel(
            {
                "message": "Here is the plan.",
                "cited_place_ids": ["mawsmai-cave"],
                "itinerary_items": [
                    {"date": "2027-01-20", "place_id": "invented-place", "start_time": "10:00:00", "end_time": "09:00:00"}
                ],
            }
        ),
    )

    result = draft_answer(
        {
            "intent": "itinerary",
            "query": "Plan a day",
            "trip_context": demo_trip_context,
            "candidates": list(candidates.values()),
        }
    )

    assert result["needs_refinement"] is True
    assert result["itinerary"] == []
    assert result["citations"] == []
    assert "couldn't validate" in result["answer"]


def test_itinerary_validator_detects_overlapping_blocks(demo_trip_context):
    candidates = _records_by_id("mawsmai-cave", "nohkalikai-falls")
    items = [
        {"date": "2027-01-16", "place_id": "mawsmai-cave", "start_time": "09:00:00", "end_time": "11:00:00"},
        {"date": "2027-01-16", "place_id": "nohkalikai-falls", "start_time": "10:30:00", "end_time": "12:00:00"},
    ]

    errors = validate_itinerary_draft(items, demo_trip_context, candidates)

    assert any("overlapping times" in error for error in errors)


class _FakeStructuredModel:
    def __init__(self, response):
        self.response = response

    def invoke(self, messages):
        return self.response


class _FakeChatModel:
    def __init__(self, response):
        self.response = response

    def with_structured_output(self, schema):
        return _FakeStructuredModel(self.response)
