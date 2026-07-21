from injector import inject
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.client.tmdb_client import TMDbClient

class MediaItemService:
    """Service for managing MediaItem business logic and TMDB imports."""

    @inject
    def __init__(self, repo: MediaItemRepository, tmdb_client: TMDbClient) -> None:
        self.repo = repo
        self.tmdb_client = tmdb_client

    def add_media_from_tmdb(self, tmdb_id: int, media_type: str) -> MediaItem:
        """Retrieves media details from TMDB and adds it to the repository if not present."""
        details = self.tmdb_client.get_details(tmdb_id, media_type)
        imdb_id = details.get("external_ids", {}).get("imdb_id")
        if not imdb_id:
            raise ValueError("L'elemento selezionato non ha un ID IMDb su TMDB.")

        media_item = self.repo.get_by_imdb_id(imdb_id)
        if not media_item:
            poster_path = details.get("poster_path")
            backdrop_path = details.get("backdrop_path")
            
            # Safe year extraction
            release_date = details.get("release_date") if media_type == "movie" else details.get("first_air_date")
            year = None
            if release_date and len(str(release_date)) >= 4:
                try:
                    year = int(str(release_date)[:4])
                except ValueError:
                    pass

            media_item = MediaItem(
                imdb_id=imdb_id,
                tmdb_id=tmdb_id,
                type=media_type,
                title=details.get("title") if media_type == "movie" else details.get("name"),
                year=year,
                description=details.get("overview"),
                poster_url=f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                background_url=f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else None
            )
            self.repo.add(media_item)
        return media_item
