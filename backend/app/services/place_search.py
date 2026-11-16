import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.schemas.place import PlaceRecord
from app.schemas.search import (
    PlaceSearchResponse,
    PlaceSearchResult,
    SearchFilters,
)

_DATA_PATH = Path(__file__).parents[1] / "data" / "places.json"
_STOP_WORDS = {
    "a", "an", "and", "are", "best", "can", "do", "for", "good", "i",
    "in", "is", "me", "my", "of", "or", "place", "places", "recommend",
    "recommendation", "recommendations", "the", "to", "visit", "we", "what",
    "with",
}


def tokenize(text: str) -> list[str]:
    """Normalize text into searchable terms and remove common query filler."""
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if token not in _STOP_WORDS
    ]


def _document_text(record: PlaceRecord) -> str:
    """Include descriptive and filter metadata in the lexical search document."""
    return " ".join(
        [
            record.name,
            record.category,
            record.area,
            record.district,
            record.summary,
            *record.tags,
        ]
    )


class PlaceSearchService:
    """Small-corpus BM25 retriever with metadata filters and a safe fallback."""

    def __init__(self, records: list[PlaceRecord]) -> None:
        self.records = records
        self.document_tokens = [tokenize(_document_text(record)) for record in records]
        self.index = BM25Okapi(self.document_tokens) if records else None

    @classmethod
    def from_json(cls, path: Path = _DATA_PATH) -> "PlaceSearchService":
        raw_records = json.loads(path.read_text(encoding="utf-8"))
        records = [PlaceRecord.model_validate(item) for item in raw_records]
        return cls(records)

    def search(
        self,
        query: str,
        *,
        filters: SearchFilters | None = None,
        top_k: int = 5,
        min_query_coverage: float = 0.2,
    ) -> PlaceSearchResponse:
        """Rank matching places, filter metadata, and abstain on weak matches."""
        active_filters = filters or SearchFilters()
        query_tokens = list(dict.fromkeys(tokenize(query)))
        filtered_indices = [
            index
            for index, record in enumerate(self.records)
            if self._matches_filters(record, active_filters)
        ]

        if not query_tokens or not filtered_indices or self.index is None:
            return self._fallback(query, active_filters)

        scores = self.index.get_scores(query_tokens)
        candidates: list[PlaceSearchResult] = []
        query_set = set(query_tokens)
        for index in filtered_indices:
            matched = sorted(query_set.intersection(self.document_tokens[index]))
            coverage = len(matched) / len(query_set)
            if scores[index] <= 0 or coverage < min_query_coverage:
                continue
            candidates.append(
                PlaceSearchResult(
                    record=self.records[index],
                    bm25_score=float(scores[index]),
                    query_coverage=coverage,
                    matched_terms=matched,
                )
            )

        candidates.sort(key=lambda item: item.bm25_score, reverse=True)
        if not candidates:
            return self._fallback(query, active_filters)

        return PlaceSearchResponse(
            query=query,
            applied_filters=active_filters,
            results=candidates[:top_k],
            needs_refinement=False,
        )

    @staticmethod
    def _matches_filters(record: PlaceRecord, filters: SearchFilters) -> bool:
        if filters.area and filters.area.casefold() not in record.area.casefold():
            return False
        if filters.category and record.category != filters.category:
            return False
        if filters.setting and record.setting != filters.setting:
            return False
        return True

    @staticmethod
    def _fallback(query: str, filters: SearchFilters) -> PlaceSearchResponse:
        return PlaceSearchResponse(
            query=query,
            applied_filters=filters,
            results=[],
            needs_refinement=True,
            fallback_message=(
                "I couldn't find a sufficiently relevant place in the current local "
                "dataset. Try another area or activity, or add more detail."
            ),
        )


place_search = PlaceSearchService.from_json()
