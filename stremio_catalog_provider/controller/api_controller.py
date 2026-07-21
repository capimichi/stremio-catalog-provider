import secrets
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from injector import inject
from stremio_catalog_provider.config.web_ui_config import WebUiConfig
from stremio_catalog_provider.client.tmdb_client import TMDbClient
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.service.torrent_service import TorrentService
from stremio_catalog_provider.service.media_item_service import MediaItemService
from stremio_catalog_provider.service.file_mapping_service import FileMappingService
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.entity.file_mapping import FileMapping

class TorrentRequest(BaseModel):
    magnet_url: str
    media_id: Optional[int] = None

class MediaImportRequest(BaseModel):
    tmdb_id: int
    type: str

class MappingUpdateRequest(BaseModel):
    media_item_id: Optional[int] = None
    season_num: Optional[int] = None
    episode_num: Optional[int] = None

class ApiController:
    """REST API Controller exposing actions for management actions (Torrents, mapping, search)."""

    @inject
    def __init__(
        self,
        config: WebUiConfig,
        torrent_service: TorrentService,
        media_item_service: MediaItemService,
        mapping_service: FileMappingService,
        media_repo: MediaItemRepository,
        torrent_repo: TorrentRepository,
        mapping_repo: FileMappingRepository,
        tmdb_client: TMDbClient
    ) -> None:
        self.config = config
        self.torrent_service = torrent_service
        self.media_item_service = media_item_service
        self.mapping_service = mapping_service
        self.media_repo = media_repo
        self.torrent_repo = torrent_repo
        self.mapping_repo = mapping_repo
        self.tmdb_client = tmdb_client
        self.router: APIRouter = APIRouter()
        self.security: HTTPBasic = HTTPBasic()
        self._register_routes()

    def verify_credentials(self, credentials: HTTPBasicCredentials) -> None:
        """Validates credentials against WebUiConfig credentials."""
        current_username_bytes = credentials.username.encode("utf8")
        correct_username_bytes = self.config.username.encode("utf8")
        is_correct_username = secrets.compare_digest(
            current_username_bytes, correct_username_bytes
        )

        current_password_bytes = credentials.password.encode("utf8")
        correct_password_bytes = self.config.password.encode("utf8")
        is_correct_password = secrets.compare_digest(
            current_password_bytes, correct_password_bytes
        )

        if not (is_correct_username and is_correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access Denied: Incorrect Credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

    def _register_routes(self) -> None:
        self.router.add_api_route("/api/torrents", self.add_torrent, methods=["POST"])
        self.router.add_api_route("/api/torrents/{info_hash}/retry", self.retry_torrent, methods=["POST"])
        self.router.add_api_route("/api/torrents/{info_hash}", self.delete_torrent, methods=["DELETE"])
        self.router.add_api_route("/api/torrents/{info_hash}/mappings", self.get_mappings, methods=["GET"])
        self.router.add_api_route("/api/mappings/{mapping_id}", self.update_mapping, methods=["PUT"])
        self.router.add_api_route("/api/tmdb/search", self.search_tmdb, methods=["GET"])
        self.router.add_api_route("/api/media", self.import_media, methods=["POST"])

    async def add_torrent(
        self, req: TorrentRequest, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Adds a torrent magnet link to processing queue."""
        self.verify_credentials(credentials)
        try:
            torrent = self.torrent_service.add_torrent(req.magnet_url, req.media_id)
            return {"status": "ok", "info_hash": torrent.info_hash}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def retry_torrent(
        self, info_hash: str, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Resets a torrent queue state back to QUEUED."""
        self.verify_credentials(credentials)
        self.torrent_service.retry_torrent(info_hash)
        return {"status": "ok"}

    async def delete_torrent(
        self, info_hash: str, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Deletes a torrent from database queue."""
        self.verify_credentials(credentials)
        self.torrent_service.delete_torrent(info_hash)
        return {"status": "ok"}

    async def get_mappings(
        self, info_hash: str, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Retrieves list of file mappings generated for a torrent."""
        self.verify_credentials(credentials)
        mappings = self.mapping_repo.get_by_torrent(info_hash)
        res = []
        session = self.mapping_repo.get_session()
        for m in mappings:
            media_title = None
            if m.media_item_id:
                media = self.media_repo.get_by_id(m.media_item_id)
                if media:
                    media_title = media.title

            episode_num = None
            season_num = None
            if m.episode_id:
                ep = session.query(Episode).filter_by(id=m.episode_id).first()
                if ep:
                    episode_num = ep.episode
                    season_num = ep.season

            res.append({
                "id": m.id,
                "file_index": m.file_index,
                "file_path": m.file_path,
                "file_size": m.file_size,
                "media_item_id": m.media_item_id,
                "media_title": media_title,
                "episode_id": m.episode_id,
                "season_num": season_num,
                "episode_num": episode_num,
                "manually_corrected": m.manually_corrected
            })
        return {"mappings": res}

    async def update_mapping(
        self, mapping_id: int, req: MappingUpdateRequest, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Manually corrects the mapping of a torrent file to a movie/series episode."""
        self.verify_credentials(credentials)
        session = self.mapping_repo.get_session()
        mapping = session.query(FileMapping).filter_by(id=mapping_id).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        mapping.media_item_id = req.media_item_id
        session.commit()

        self.mapping_service.remap_file(mapping_id, req.episode_num, req.season_num)
        return {"status": "ok"}

    async def search_tmdb(
        self, query: str, type: str, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Queries TMDB API directly for matching metadata."""
        self.verify_credentials(credentials)
        try:
            results = self.tmdb_client.search_media(query, type)
            return {"results": results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def import_media(
        self, req: MediaImportRequest, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> dict[str, Any]:
        """Triggers local import of metadata for a selected TMDB item."""
        self.verify_credentials(credentials)
        try:
            media = self.media_item_service.add_media_from_tmdb(req.tmdb_id, req.type)
            return {"status": "ok", "media_id": media.id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
