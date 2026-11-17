from app.schemas.search import SearchFilters
from app.services.place_search import place_search


def test_fossil_cave_query_retrieves_arwah_with_source():
    response = place_search.search(
        "fossils cave Sohra",
        filters=SearchFilters(area="Sohra", category="cave"),
        top_k=3,
    )

    result_ids = [result.record.id for result in response.results]
    assert "arwah-cave" in result_ids
    arwah = next(result.record for result in response.results if result.record.id == "arwah-cave")
    assert "meghalayatourism.in" in str(arwah.source.url)


def test_metadata_filter_limits_results_to_mixed_setting():
    response = place_search.search(
        "cave fossils",
        filters=SearchFilters(setting="mixed"),
        top_k=5,
    )

    assert response.results
    assert all(result.record.setting == "mixed" for result in response.results)
    assert any(result.record.id == "arwah-cave" for result in response.results)


def test_unsupported_query_abstains_instead_of_returning_a_random_place():
    response = place_search.search("sushi in Shillong")

    assert response.results == []
    assert response.needs_refinement is True
    assert response.fallback_message
