import json
import math
from pathlib import Path

from app.schemas.search import SearchFilters
from app.services.place_search import place_search

CASE_PATH = Path(__file__).with_name("retrieval_cases.json")
TOP_K = 3


def ndcg_at_k(retrieved: list[str], relevance: dict[str, int], k: int) -> float | None:
    """Compute nDCG using graded relevance labels (0 = irrelevant)."""
    if not relevance:
        return None

    def dcg(gains: list[int]) -> float:
        return sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))

    actual_gains = [relevance.get(place_id, 0) for place_id in retrieved[:k]]
    ideal_gains = sorted(relevance.values(), reverse=True)[:k]
    ideal_dcg = dcg(ideal_gains)
    return dcg(actual_gains) / ideal_dcg if ideal_dcg else 0.0


def evaluate_case(case: dict) -> dict:
    response = place_search.search(
        case["query"],
        filters=SearchFilters(**case.get("filters", {})),
        top_k=TOP_K,
    )
    retrieved = [result.record.id for result in response.results]
    relevance = case["relevance"]
    relevant_ids = {place_id for place_id, grade in relevance.items() if grade > 0}
    relevant_hits = [place_id for place_id in retrieved if place_id in relevant_ids]
    precision = len(relevant_hits) / TOP_K
    recall = len(relevant_hits) / len(relevant_ids) if relevant_ids else None
    reciprocal_rank = next(
        (1 / rank for rank, place_id in enumerate(retrieved, start=1) if place_id in relevant_ids),
        0.0 if relevant_ids else None,
    )
    return {
        "name": case["name"],
        "relevance": relevance,
        "retrieved": retrieved,
        "precision_at_k": precision,
        "recall_at_k": recall,
        "reciprocal_rank": reciprocal_rank,
        "ndcg_at_k": ndcg_at_k(retrieved, relevance, TOP_K),
        "correct_abstention": not relevant_ids and response.needs_refinement,
        "needs_refinement": response.needs_refinement,
    }


def main() -> None:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]
    positive_cases = [result for result in results if result["recall_at_k"] is not None]
    no_match_cases = [result for result in results if result["recall_at_k"] is None]

    for result in results:
        print(
            f"{result['name']}: retrieved={result['retrieved']} "
            f"nDCG@{TOP_K}={result['ndcg_at_k']} "
            f"P@{TOP_K}={result['precision_at_k']:.2f} "
            f"R@{TOP_K}={result['recall_at_k']} "
            f"RR={result['reciprocal_rank']} "
            f"refine={result['needs_refinement']}"
        )
    print(f"Macro Precision@{TOP_K}: {sum(r['precision_at_k'] for r in positive_cases) / len(positive_cases):.3f}")
    print(f"Macro Recall@{TOP_K}: {sum(r['recall_at_k'] for r in positive_cases) / len(positive_cases):.3f}")
    print(f"MRR@{TOP_K}: {sum(r['reciprocal_rank'] for r in positive_cases) / len(positive_cases):.3f}")
    print(f"Macro nDCG@{TOP_K}: {sum(r['ndcg_at_k'] for r in positive_cases) / len(positive_cases):.3f}")
    if no_match_cases:
        correct = sum(result["correct_abstention"] for result in no_match_cases)
        print(f"Correct abstention: {correct}/{len(no_match_cases)}")


if __name__ == "__main__":
    main()
