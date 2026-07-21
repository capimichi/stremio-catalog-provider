from typing import Any, Optional
import httpx
from injector import inject
from stremio_catalog_provider.config.tmdb_config import TMDbConfig

class TMDbClient:
    """HTTP Client for communicating with the TheMovieDatabase (TMDb) API."""

    @inject
    def __init__(self, config: TMDbConfig) -> None:
        self.config = config
        self.base_url: str = "https://api.themoviedb.org/3"

    def search_media(self, query: str, media_type: str, year: Optional[int] = None) -> list[dict[str, Any]]:
        """Searches movies or series on TMDb."""
        tmdb_type = "tv" if media_type == "series" else media_type
        endpoint = f"{self.base_url}/search/{tmdb_type}"
        params: dict[str, Any] = {
            "api_key": self.config.api_key,
            "query": query,
            "language": "it-IT"
        }
        if year:
            params["year" if tmdb_type == "movie" else "first_air_date_year"] = year

        response = httpx.get(endpoint, params=params, timeout=30.0)
        response.raise_for_status()
        results = response.json().get("results", [])
        if isinstance(results, list):
            return results
        return []

    def get_details(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
        """Retrieves details of a movie or series, including external IDs (like IMDb ID)."""
        tmdb_type = "tv" if media_type == "series" else media_type
        endpoint = f"{self.base_url}/{tmdb_type}/{tmdb_id}"
        params: dict[str, Any] = {
            "api_key": self.config.api_key,
            "language": "it-IT",
            "append_to_response": "external_ids"
        }
        response = httpx.get(endpoint, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {}
