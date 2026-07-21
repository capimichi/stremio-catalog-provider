from typing import Any
from injector import inject
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.entity.file_mapping import FileMapping

class StremioService:
    """Service to handle Stremio catalog, metadata and stream requests."""

    @inject
    def __init__(
        self,
        media_repo: MediaItemRepository,
        mapping_repo: FileMappingRepository,
        torr_config: TorrServerConfig
    ) -> None:
        self.media_repo = media_repo
        self.mapping_repo = mapping_repo
        self.torr_config = torr_config

    def get_manifest(self) -> dict[str, Any]:
        """Returns the Stremio Addon manifest."""
        return {
            "id": "org.stremio.custom.catalog",
            "version": "1.0.0",
            "name": "Custom Torrents Catalog",
            "description": "Fornisce streaming diretto da TorrServer per magnet caricati.",
            "resources": ["catalog", "meta", "stream"],
            "types": ["movie", "series"],
            "catalogs": [
                {"type": "movie", "id": "custom_movies", "name": "Film Personali"},
                {"type": "series", "id": "custom_series", "name": "Serie Personali"}
            ],
            "idPrefixes": ["tt"]
        }

    def get_catalog(self, media_type: str) -> dict[str, Any]:
        """Returns metadata list for the requested type (movie or series) catalog."""
        items = self.media_repo.search_local(query="", media_type=media_type)
        metas = []
        for item in items:
            metas.append({
                "id": item.imdb_id,
                "type": item.type,
                "name": item.title,
                "poster": item.poster_url,
                "background": item.background_url,
                "description": item.description
            })
        return {"metas": metas}

    def get_meta(self, media_type: str, imdb_id: str) -> dict[str, Any]:
        """Returns detailed metadata and episode lists for a specific movie or series."""
        media = self.media_repo.get_by_imdb_id(imdb_id)
        if not media:
            return {"meta": {}}

        meta: dict[str, Any] = {
            "id": media.imdb_id,
            "type": media.type,
            "name": media.title,
            "poster": media.poster_url,
            "background": media.background_url,
            "description": media.description
        }

        if media.type == "series":
            mappings = self.mapping_repo.get_by_media_item(media.id)
            videos = []
            seen_episodes = set()
            session = self.mapping_repo.get_session()
            for m in mappings:
                if m.episode_id:
                    ep = session.query(Episode).filter_by(id=m.episode_id).first()
                    if ep and (ep.season, ep.episode) not in seen_episodes:
                        seen_episodes.add((ep.season, ep.episode))
                        videos.append({
                            "id": f"{media.imdb_id}:{ep.season}:{ep.episode}",
                            "season": ep.season,
                            "episode": ep.episode,
                            "title": f"Stagione {ep.season} Episodio {ep.episode}"
                        })
            meta["videos"] = sorted(videos, key=lambda x: (x["season"], x["episode"]))
        return {"meta": meta}

    def get_stream(self, media_type: str, stream_id: str) -> dict[str, Any]:
        """Returns available video streams for a specific movie or TV series episode."""
        streams = []
        session = self.mapping_repo.get_session()

        if media_type == "movie":
            media = self.media_repo.get_by_imdb_id(stream_id)
            if media:
                mappings = session.query(FileMapping).filter_by(media_item_id=media.id).all()
                for m in mappings:
                    stream_url = f"{self.torr_config.base_url}/stream?link={m.file_index}&hash={m.torrent_hash}&play"
                    streams.append({
                        "title": f"Stream {m.file_path} ({round(m.file_size / 1024 / 1024, 2)} MB)",
                        "url": stream_url
                    })
        elif media_type == "series":
            # stream_id format is imdb_id:season:episode
            parts = stream_id.split(":")
            if len(parts) == 3:
                imdb_id, season_num, episode_num = parts[0], int(parts[1]), int(parts[2])
                media = self.media_repo.get_by_imdb_id(imdb_id)
                if media:
                    ep = session.query(Episode).filter_by(
                        media_item_id=media.id, season=season_num, episode=episode_num
                    ).first()
                    if ep:
                        mappings = session.query(FileMapping).filter_by(episode_id=ep.id).all()
                        for m in mappings:
                            stream_url = f"{self.torr_config.base_url}/stream?link={m.file_index}&hash={m.torrent_hash}&play"
                            streams.append({
                                "title": f"Episodio {episode_num} - {m.file_path} ({round(m.file_size / 1024 / 1024, 2)} MB)",
                                "url": stream_url
                            })
        return {"streams": streams}
