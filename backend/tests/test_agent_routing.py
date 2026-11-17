import pytest

from app.agent import graph as assistant_graph_module
from app.agent.graph import choose_path, draft_answer, route_request
from app.services.place_search import place_search


@pytest.mark.parametrize(
    ("intent", "expected_path"),
    [
        ("recommendation", "search"),
        ("itinerary", "search"),
        ("weather", "weather"),
        ("clarification", "clarify"),
    ],
)
def test_intent_selects_expected_graph_path(intent, expected_path):
    assert choose_path({"intent": intent}) == expected_path


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


def test_route_node_accepts_structured_dictionary(monkeypatch):
    monkeypatch.setattr(
        assistant_graph_module,
        "get_chat_model",
        lambda: _FakeChatModel(
            {
                "intent": "weather",
                "retrieval_query": "",
                "area": None,
                "weather_location": "Sohra",
                "category": None,
                "setting": None,
                "clarification_question": "",
            }
        ),
    )

    result = route_request({"query": "Weather tomorrow?", "trip_context": {}})

    assert result["intent"] == "weather"
    assert result["route_decision"]["weather_location"] == "Sohra"


def test_answer_node_discards_citation_ids_not_in_retrieval(monkeypatch):
    record = place_search.search("fossils cave", top_k=1).results[0].record
    monkeypatch.setattr(
        assistant_graph_module,
        "get_chat_model",
        lambda: _FakeChatModel(
            {"message": "Arwah Cave is a fossil-rich cave.", "cited_place_ids": ["invented-place"]}
        ),
    )

    result = draft_answer(
        {
            "intent": "recommendation",
            "query": "Tell me about this cave",
            "trip_context": {},
            "candidates": [record.model_dump(mode="json")],
        }
    )

    assert result["citations"]
    assert {citation["source_id"] for citation in result["citations"]} == {record.id}
