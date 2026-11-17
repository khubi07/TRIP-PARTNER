from pathlib import Path

import pytest

from app.schemas.trip_context import TripContext
from app.services.trip_store import TripStore


DATA_PATH = Path(__file__).parents[1] / "app" / "data" / "demo_trip_context.json"


def _seed_context():
    return TripContext.model_validate_json(DATA_PATH.read_text(encoding="utf-8"))


def _pending_event():
    return {
        "event_id": "event-test-001",
        "trip_id": "trip-demo-001",
        "forecast_date": "2027-01-16",
        "event_source": "simulated",
        "status": "suggestion_created",
        "precipitation_change": 65,
        "affected_item_ids": ["item-demo-002"],
        "message": "Approve the proposed cave alternative?",
        "suggested_alternative": {
            "place_id": "arwah-cave",
            "title": "Arwah Cave",
            "area": "Sohra (Cherrapunji)",
            "summary": "A fossil-rich cave.",
            "setting": "mixed",
        },
        "citations": [],
        "requires_guest_approval": True,
        "approval_status": "pending",
        "llm_used": True,
    }


def test_approval_persists_replacement_and_decision(tmp_path):
    store = TripStore(tmp_path / "trip-test.sqlite3")
    seed = _seed_context()
    store.get_trip_context(seed)
    store.save_weather_event("event-test-001", seed.trip_id, _pending_event())

    result = store.decide_weather_event("event-test-001", "approve")
    saved_trip = store.get_trip_context(seed)
    updated_item = next(item for item in saved_trip.itinerary if item.item_id == "item-demo-002")

    assert result["approval_status"] == "approved"
    assert result["requires_guest_approval"] is False
    assert updated_item.title == "Arwah Cave"
    assert updated_item.place_id == "arwah-cave"
    assert updated_item.setting == "mixed"


def test_rejection_leaves_itinerary_unchanged(tmp_path):
    store = TripStore(tmp_path / "trip-test.sqlite3")
    seed = _seed_context()
    store.get_trip_context(seed)
    store.save_weather_event("event-test-001", seed.trip_id, _pending_event())

    result = store.decide_weather_event("event-test-001", "reject")
    saved_trip = store.get_trip_context(seed)
    unchanged_item = next(item for item in saved_trip.itinerary if item.item_id == "item-demo-002")

    assert result["approval_status"] == "rejected"
    assert unchanged_item.title == "Nohkalikai Falls viewpoint"
    assert unchanged_item.place_id == "nohkalikai-falls"


def test_decision_is_one_time_only(tmp_path):
    store = TripStore(tmp_path / "trip-test.sqlite3")
    seed = _seed_context()
    store.get_trip_context(seed)
    store.save_weather_event("event-test-001", seed.trip_id, _pending_event())
    store.decide_weather_event("event-test-001", "reject")

    with pytest.raises(ValueError, match="already been decided"):
        store.decide_weather_event("event-test-001", "approve")
