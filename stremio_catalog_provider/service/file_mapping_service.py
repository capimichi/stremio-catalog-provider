from typing import Optional
from injector import inject
from stremio_catalog_provider.entity.file_mapping import FileMapping
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.repository.episode_repository import EpisodeRepository

class FileMappingService:
    """Service to handle updating and correcting file mappings manually."""

    @inject
    def __init__(self, repo: FileMappingRepository, episode_repo: EpisodeRepository) -> None:
        self.repo = repo
        self.episode_repo = episode_repo

    def remap_file(
        self, mapping_id: int, episode_num: Optional[int], season_num: Optional[int]
    ) -> None:
        """Remaps a specific file mapping to a different episode or resets it for a movie."""
        session = self.repo.get_session()
        mapping = session.query(FileMapping).filter_by(id=mapping_id).first()
        if not mapping:
            return

        if season_num is not None and episode_num is not None and mapping.media_item_id is not None:
            # TV Series episode mapping
            episode = self.episode_repo.get_or_create(
                mapping.media_item_id, season_num, episode_num
            )
            mapping.episode_id = episode.id
        else:
            # Movie mapping (no episode association)
            mapping.episode_id = None

        mapping.manually_corrected = True
        session.commit()
