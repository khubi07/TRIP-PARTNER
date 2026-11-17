from copy import deepcopy

from app.agent.weather_event_graph import (
    choose_event_path,
    evaluate_weather_impact,
    find_indoor_alternatives,
)


def _event(date="2027-01-16", previous=20, current=85):
    return {
        "trip_id": "trip-demo-001",
        "forecast_date": date,
        "previous_precipitation_probability": previous,
        "current_precipitation_probability": current,
        "area": "Sohra",
        "event_source": "simulated",
    }


def test_significant_rain_change_for_outdoor_item_routes_to_search(demo_trip_context):
    state = evaluate_weather_impact(
        {"event": _event(), "trip_context": demo_trip_context}
    )

    assert state["impact_detected"] is True
    assert [item["item_id"] for item in state["affected_items"]] == ["item-demo-002"]
    assert choose_event_path(state) == "search"


def test_change_below_threshold_does_not_trigger_search(demo_trip_context):
    state = evaluate_weather_impact(
        {
            "event": _event(previous=40, current=59),
            "trip_context": demo_trip_context,
        }
    )

    assert state["impact_detected"] is False
    assert state["llm_used"] is False
    assert choose_event_path(state) == "finish"


def test_rain_on_a_date_without_outdoor_activity_does_not_trigger(demo_trip_context):
    state = evaluate_weather_impact(
        {
            "event": _event(date="2027-01-17"),
            "trip_context": demo_trip_context,
        }
    )

    assert state["impact_detected"] is False
    assert state["affected_items"] == []


def test_alternative_search_excludes_place_already_on_same_day(demo_trip_context):
    state = find_indoor_alternatives(
        {"event": _event(), "trip_context": deepcopy(demo_trip_context)}
    )

    candidate_ids = [candidate["id"] for candidate in state["candidates"]]
    assert "mawsmai-cave" not in candidate_ids
    assert "arwah-cave" in candidate_ids
