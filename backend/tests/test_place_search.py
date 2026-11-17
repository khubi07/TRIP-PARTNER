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


def test_conversational_filler_does_not_add_unrelated_places():
    response = place_search.search("Where can I see a living root bridge?")

    assert [result.record.id for result in response.results] == ["mawlynnong-village"]


def test_generic_preposition_does_not_create_a_taxi_search_match():
    response = place_search.search("book a taxi from the airport")

    assert response.results == []
    assert response.needs_refinement is True


def test_vegetarian_restaurant_query_retrieves_sourced_orange_roots():
    response = place_search.search(
        "quiet dinner place near Sohra with vegetarian options",
        filters=SearchFilters(area="Sohra", category="restaurant"),
        top_k=3,
    )

    assert response.results
    assert response.results[0].record.id == "orange-roots"
    assert "cherrapunjee.com" in str(response.results[0].record.source.url)
