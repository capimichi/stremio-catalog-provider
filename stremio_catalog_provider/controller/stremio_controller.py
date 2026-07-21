from typing import Any
from fastapi import APIRouter
from injector import inject
from stremio_catalog_provider.service.stremio_service import StremioService

class StremioController:
    """Controller exposing Stremio Addon manifest, catalog, meta, and stream API endpoints."""

    @inject
    def __init__(self, stremio_service: StremioService) -> None:
        self.stremio_service = stremio_service
        self.router: APIRouter = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("/manifest.json", self.manifest, methods=["GET"])
        self.router.add_api_route(
            "/catalog/{media_type}/{catalog_id}.json", self.catalog, methods=["GET"]
        )
        self.router.add_api_route("/meta/{media_type}/{imdb_id}.json", self.meta, methods=["GET"])
        self.router.add_api_route(
            "/stream/{media_type}/{stream_id}.json", self.stream, methods=["GET"]
        )

    async def manifest(self) -> dict[str, Any]:
        """Serves the Stremio Addon manifest."""
        return self.stremio_service.get_manifest()

    async def catalog(self, media_type: str, catalog_id: str) -> dict[str, Any]:
        """Serves a requested media catalog category (movies or series)."""
        return self.stremio_service.get_catalog(media_type)

    async def meta(self, media_type: str, imdb_id: str) -> dict[str, Any]:
        """Serves metadata details of a specific media item."""
        return self.stremio_service.get_meta(media_type, imdb_id)

    async def stream(self, media_type: str, stream_id: str) -> dict[str, Any]:
        """Serves available streams for a movie or a TV episode."""
        return self.stremio_service.get_stream(media_type, stream_id)
