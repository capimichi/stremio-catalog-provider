import respx
import httpx
from stremio_catalog_provider.config.tmdb_config import TMDbConfig
from stremio_catalog_provider.client.tmdb_client import TMDbClient

@respx.mock
def test_search_media_success() -> None:
    respx.get("https://api.themoviedb.org/3/search/movie").mock(
        return_value=httpx.Response(200, json={"results": [{"id": 123, "title": "Inception"}]})
    )

    client = TMDbClient(TMDbConfig("dummy"))
    results = client.search_media("Inception", "movie")
    assert len(results) == 1
    assert results[0]["id"] == 123

@respx.mock
def test_get_details_success() -> None:
    respx.get("https://api.themoviedb.org/3/movie/123").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 123,
                "title": "Inception",
                "external_ids": {"imdb_id": "tt1375666"}
            }
        )
    )

    client = TMDbClient(TMDbConfig("dummy"))
    details = client.get_details(123, "movie")
    assert details["id"] == 123
    assert details["external_ids"]["imdb_id"] == "tt1375666"
