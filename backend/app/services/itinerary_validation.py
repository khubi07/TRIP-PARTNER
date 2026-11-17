from datetime import date, time
from typing import Any


def validate_itinerary_draft(
    items: list[dict[str, Any]],
    trip_context: dict[str, Any],
    records_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Reject proposed stops outside the trip, outside retrieval, or overlapping."""
    errors: list[str] = []
    try:
        check_in = date.fromisoformat(trip_context["check_in"])
        check_out = date.fromisoformat(trip_context["check_out"])
    except (KeyError, TypeError, ValueError):
        return ["Trip dates are missing or invalid."]

    schedules: dict[date, list[tuple[time, time, str]]] = {}
    seen: set[tuple[date, str]] = set()
    for index, item in enumerate(items, start=1):
        try:
            item_date = date.fromisoformat(str(item["date"]))
        except (KeyError, TypeError, ValueError):
            errors.append(f"Stop {index} has an invalid date.")
            continue

        place_id = str(item.get("place_id", ""))
        if item_date < check_in or item_date > check_out:
            errors.append(f"Stop {index} falls outside the booked trip dates.")
        if place_id not in records_by_id:
            errors.append(f"Stop {index} does not match a retrieved place.")
        if (item_date, place_id) in seen:
            errors.append(f"Stop {index} repeats a place on the same day.")
        seen.add((item_date, place_id))

        start_raw = item.get("start_time")
        end_raw = item.get("end_time")
        if bool(start_raw) != bool(end_raw):
            errors.append(f"Stop {index} must have both start and end times, or neither.")
            continue
        if not start_raw:
            continue
        try:
            start_time = time.fromisoformat(str(start_raw).removesuffix("Z")).replace(tzinfo=None)
            end_time = time.fromisoformat(str(end_raw).removesuffix("Z")).replace(tzinfo=None)
        except ValueError:
            errors.append(f"Stop {index} has an invalid time.")
            continue
        if start_time >= end_time:
            errors.append(f"Stop {index} ends before it starts.")
            continue
        schedules.setdefault(item_date, []).append((start_time, end_time, f"stop {index}"))

    for day, day_schedule in schedules.items():
        ordered = sorted(day_schedule)
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] < previous[1]:
                errors.append(f"The itinerary has overlapping times on {day.isoformat()}.")
                break
    return errors
