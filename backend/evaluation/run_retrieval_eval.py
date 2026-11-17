import json
from pathlib import Path

from app.schemas.search import SearchFilters
from app.services.place_search import place_search

CASE_PATH = Path(__file__).with_name("retrieval_cases.json")
TOP_K = 3


def evaluate_case(case: dict) -> dict:
    response = place_search.search(
        case["query"],
        filters=SearchFilters(**case.get("filters", {})),
        top_k=TOP_K,
    )
    retrieved = [result.record.id for result in response.results]
    expected = case["expected_place_ids"]
    relevant_hits = [place_id for place_id in retrieved if place_id in expected]
    precision = len(relevant_hits) / TOP_K
    recall = len(relevant_hits) / len(expected) if expected else None
    reciprocal_rank = next(
        (1 / rank for rank, place_id in enumerate(retrieved, start=1) if place_id in expected),
        0.0 if expected else None,
    )
    return {
        "name": case["name"],
        "expected": expected,
        "retrieved": retrieved,
        "precision_at_k": precision,
        "recall_at_k": recall,
        "reciprocal_rank": reciprocal_rank,
        "correct_abstention": not expected and response.needs_refinement,
    }


def main() -> None:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]
    positive_cases = [result for result in results if result["recall_at_k"] is not None]
    no_match_cases = [result for result in results if result["recall_at_k"] is None]

    for result in results:
        print(
            f"{result['name']}: retrieved={result['retrieved']} "
            f"expected={result['expected']} "
            f"P@{TOP_K}={result['precision_at_k']:.2f} "
            f"R@{TOP_K}={result['recall_at_k']} "
            f"RR={result['reciprocal_rank']}"
        )
    print(f"Macro Precision@{TOP_K}: {sum(r['precision_at_k'] for r in positive_cases) / len(positive_cases):.3f}")
    print(f"Macro Recall@{TOP_K}: {sum(r['recall_at_k'] for r in positive_cases) / len(positive_cases):.3f}")
    print(f"MRR@{TOP_K}: {sum(r['reciprocal_rank'] for r in positive_cases) / len(positive_cases):.3f}")
    if no_match_cases:
        correct = sum(result["correct_abstention"] for result in no_match_cases)
        print(f"Correct abstention: {correct}/{len(no_match_cases)}")


if __name__ == "__main__":
    main()
