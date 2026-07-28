import secrets
from typing import Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from injector import inject
from stremio_catalog_provider.config.web_ui_config import WebUiConfig
from stremio_catalog_provider.config.app_config import AppConfig
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.repository.episode_repository import EpisodeRepository
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.entity.file_mapping import FileMapping

class WebUiController:
    """Controller rendering Jinja2 HTML templates for the admin dashboard panel."""

    @inject
    def __init__(
        self,
        config: WebUiConfig,
        app_config: AppConfig,
        media_repo: MediaItemRepository,
        torrent_repo: TorrentRepository,
        mapping_repo: FileMappingRepository,
        episode_repo: EpisodeRepository
    ) -> None:
        self.config = config
        self.app_config = app_config
        self.media_repo = media_repo
        self.torrent_repo = torrent_repo
        self.mapping_repo = mapping_repo
        self.episode_repo = episode_repo
        self.router: APIRouter = APIRouter()
        self.templates: Jinja2Templates = Jinja2Templates(directory="templates")
        self.security: HTTPBasic = HTTPBasic()
        self._register_routes()

    def verify_credentials(self, credentials: HTTPBasicCredentials) -> None:
        """Validates credentials against configured WebUiConfig basic auth."""
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
        self.router.add_api_route("/", self.root_redirect, methods=["GET"])
        self.router.add_api_route("/dashboard", self.dashboard, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/media", self.media, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/media/add", self.media_add, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/media/{media_id}", self.media_details, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/torrents", self.torrents, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/torrents/{torrent_id}/edit", self.torrent_edit, methods=["GET"], response_class=HTMLResponse)
        self.router.add_api_route("/remap/{mapping_id}", self.remap, methods=["GET"], response_class=HTMLResponse)

    async def dashboard(
        self, request: Request, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the dashboard metrics page."""
        self.verify_credentials(credentials)
        torrents = self.torrent_repo.get_all()
        movies = self.media_repo.search_local(query="", media_type="movie")
        series = self.media_repo.search_local(query="", media_type="series")

        queued = sum(1 for t in torrents if t.status == "QUEUED")
        processing = sum(1 for t in torrents if t.status == "PROCESSING")
        processed = sum(1 for t in torrents if t.status == "PROCESSED")
        failed = sum(1 for t in torrents if t.status == "FAILED")

        base_url = self.app_config.base_url or str(request.base_url)
        if not base_url.endswith("/"):
            base_url += "/"
        stremio_url = f"{base_url}manifest.json"

        return self.templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "active_page": "dashboard",
                "stremio_url": stremio_url,
                "movie_count": len(movies),
                "series_count": len(series),
                "torrent_count": len(torrents),
                "queued_count": queued,
                "processing_count": processing,
                "processed_count": processed,
                "failed_count": failed
            }
        )

    async def media(
        self, request: Request, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the media grid gallery page."""
        self.verify_credentials(credentials)
        media_items = self.media_repo.search_local(query="")
        return self.templates.TemplateResponse(
            request,
            "media.html",
            {
                "active_page": "media",
                "media_items": media_items
            }
        )

    async def media_add(
        self, request: Request, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the page to add/import a new MediaItem from TMDB."""
        self.verify_credentials(credentials)
        return self.templates.TemplateResponse(
            request,
            "media_add.html",
            {
                "active_page": "media"
            }
        )

    async def media_details(
        self, request: Request, media_id: int, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the detailed overview of a single MediaItem."""
        self.verify_credentials(credentials)
        media = self.media_repo.get_by_id(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Find torrents associated with this media item
        all_mappings = self.mapping_repo.get_by_media_item(media_id)
        torrents = {m.torrent for m in all_mappings if m.torrent is not None}
        torrents = sorted(list(torrents), key=lambda x: x.added_at, reverse=True)

        return self.templates.TemplateResponse(
            request,
            "media_details.html",
            {
                "active_page": "media",
                "media": media,
                "torrents": torrents
            }
        )

    async def torrents(
        self, request: Request, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the global torrent process queue monitor page."""
        self.verify_credentials(credentials)
        torrents = self.torrent_repo.get_all()
        return self.templates.TemplateResponse(
            request,
            "torrents.html",
            {
                "active_page": "torrents",
                "torrents": torrents
            }
        )

    async def remap(
        self, request: Request, mapping_id: int, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the manual mapping config page for a file."""
        self.verify_credentials(credentials)
        session = self.mapping_repo.get_session()
        mapping = session.query(FileMapping).filter_by(id=mapping_id).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        torrent = mapping.torrent
        media = self.media_repo.get_by_id(mapping.media_item_id) if mapping.media_item_id else None
        episode = session.query(Episode).filter_by(id=mapping.episode_id).first() if mapping.episode_id else None
        all_media = self.media_repo.search_local(query="")

        return self.templates.TemplateResponse(
            request,
            "remap.html",
            {
                "active_page": "torrents",
                "mapping": mapping,
                "torrent": torrent,
                "media": media,
                "episode": episode,
                "all_media": all_media
            }
        )

    async def torrent_edit(
        self, request: Request, torrent_id: int, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ) -> Any:
        """Renders the torrent edit details page."""
        self.verify_credentials(credentials)
        torrent = self.torrent_repo.get_by_id(torrent_id)
        if not torrent:
            raise HTTPException(status_code=404, detail="Torrent not found")
        all_media = self.media_repo.search_local(query="")
        return self.templates.TemplateResponse(
            request,
            "torrent_edit.html",
            {
                "active_page": "torrents",
                "torrent": torrent,
                "all_media": all_media
            }
        )

    async def root_redirect(self) -> RedirectResponse:
        """Redirects root path to dashboard page."""
        return RedirectResponse(url="/dashboard")

