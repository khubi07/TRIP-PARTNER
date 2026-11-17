import json
from pathlib import Path

from app.agent.graph import route_request
from app.schemas.trip_context import TripContext


HERE = Path(__file__).parent
CONTEXT_PATH = HERE.parent / "app" / "data" / "demo_trip_context.json"
CASES_PATH = HERE / "routing_cases.json"


def main() -> None:
    trip_context = TripContext.model_validate_json(
        CONTEXT_PATH.read_text(encoding="utf-8")
    ).model_dump(mode="json")
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    correct = 0

    for case in cases:
        result = route_request(
            {"query": case["query"], "trip_context": trip_context}
        )
        actual = result.get("intent", "")
        passed = actual == case["expected_intent"]
        correct += int(passed)
        print(
            f"{'PASS' if passed else 'FAIL'} {case['name']}: "
            f"expected={case['expected_intent']} actual={actual}"
        )

    print(f"Intent accuracy: {correct}/{len(cases)} ({correct / len(cases):.1%})")


if __name__ == "__main__":
    main()
