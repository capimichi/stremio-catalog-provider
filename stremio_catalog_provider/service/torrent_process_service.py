import time
from datetime import datetime
from typing import Optional
from injector import inject
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.repository.episode_repository import EpisodeRepository
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.client.torrserver_client import TorrServerClient
from stremio_catalog_provider.client.tmdb_client import TMDbClient
from stremio_catalog_provider.service.torrent_parser_service import TorrentParserService
from stremio_catalog_provider.service.media_item_service import MediaItemService
from stremio_catalog_provider.entity.file_mapping import FileMapping

class TorrentProcessService:
    """Service responsible for processing the queued torrents and resolving their metadata."""

    @inject
    def __init__(
        self,
        torrent_repo: TorrentRepository,
        media_repo: MediaItemRepository,
        episode_repo: EpisodeRepository,
        mapping_repo: FileMappingRepository,
        torr_client: TorrServerClient,
        tmdb_client: TMDbClient,
        parser_service: TorrentParserService,
        media_item_service: MediaItemService
    ) -> None:
        self.torrent_repo = torrent_repo
        self.media_repo = media_repo
        self.episode_repo = episode_repo
        self.mapping_repo = mapping_repo
        self.torr_client = torr_client
        self.tmdb_client = tmdb_client
        self.parser_service = parser_service
        self.media_item_service = media_item_service

    def process_next_torrent(
        self, poll_timeout: float = 300.0, poll_interval: float = 5.0
    ) -> bool:
        """Pulls the next QUEUED torrent, adds it to TorrServer, resolves files and maps them to media items."""
        torrent = self.torrent_repo.get_next_queued_for_update()
        if not torrent:
            return False

        session = self.torrent_repo.get_session()
        try:
            # 1. Add magnet link to TorrServer
            info_hash = self.torr_client.add_torrent(torrent.magnet_url)
            if info_hash != torrent.info_hash:
                torrent.info_hash = info_hash

            # 2. Polling for file list resolution
            start_time = time.time()
            files = []
            while time.time() - start_time < poll_timeout:
                files = self.torr_client.get_torrent_files(torrent.info_hash)
                if files:
                    break
                time.sleep(poll_interval)

            if not files:
                raise TimeoutError("TorrServer did not resolve the file list within the timeout.")

            # 3. Filter and process video files
            video_extensions = (".mkv", ".mp4", ".avi", ".mov")
            media_cache = {}  # Local cache to prevent redundant TMDB queries for files in the same torrent
            
            for f in files:
                file_path = f.get("path", "")
                if not file_path.lower().endswith(video_extensions):
                    continue

                # Parse filename to extract title/season/episode
                parsed = self.parser_service.parse_filename(file_path.split("/")[-1])

                media_item = None
                if torrent.predefined_media_item_id:
                    media_item = self.media_repo.get_by_id(torrent.predefined_media_item_id)
                else:
                    search_type = "series" if parsed["season"] is not None else "movie"
                    cache_key = (parsed["title"].lower().strip(), search_type)
                    
                    if cache_key in media_cache:
                        media_item = media_cache[cache_key]
                    else:
                        # Auto search on TMDB
                        results = self.tmdb_client.search_media(
                            parsed["title"], search_type, parsed["year"]
                        )
                        if results:
                            tmdb_id = results[0]["id"]
                            try:
                                media_item = self.media_item_service.add_media_from_tmdb(
                                    tmdb_id, search_type
                                )
                            except Exception:
                                pass
                        media_cache[cache_key] = media_item

                # Create file mapping record
                mapping = FileMapping(
                    torrent_hash=torrent.info_hash,
                    file_index=f.get("id"),
                    file_path=file_path,
                    file_size=f.get("size", 0),
                    media_item_id=media_item.id if media_item else None
                )

                if (
                    media_item
                    and media_item.type == "series"
                    and parsed["season"] is not None
                    and parsed["episode"] is not None
                ):
                    episode = self.episode_repo.get_or_create(
                        media_item.id, parsed["season"], parsed["episode"]
                    )
                    mapping.episode_id = episode.id

                self.mapping_repo.add(mapping)

            torrent.status = "PROCESSED"
            torrent.processed_at = datetime.utcnow()
            session.commit()

        except Exception as e:
            torrent.status = "FAILED"
            torrent.error_message = str(e)
            session.commit()
            # Try cleaning up from TorrServer if failed
            try:
                self.torr_client.remove_torrent(torrent.info_hash)
            except Exception:
                pass
        return True
