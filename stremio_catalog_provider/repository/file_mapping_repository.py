from injector import inject
from sqlalchemy.orm import Session
from stremio_catalog_provider.entity.file_mapping import FileMapping
from stremio_catalog_provider.manager.db_manager import DbManager

class FileMappingRepository:
    """Repository class for FileMapping entity database operations."""

    @inject
    def __init__(self, db_manager: DbManager) -> None:
        self.db_manager = db_manager

    def get_session(self) -> Session:
        return self.db_manager.get_session()

    def add(self, mapping: FileMapping) -> None:
        session = self.get_session()
        session.add(mapping)
        session.commit()

    def get_by_torrent(self, torrent_hash: str) -> list[FileMapping]:
        return self.get_session().query(FileMapping).filter_by(torrent_hash=torrent_hash).all()

    def get_by_media_item(self, media_item_id: int) -> list[FileMapping]:
        return self.get_session().query(FileMapping).filter_by(media_item_id=media_item_id).all()

    def get_by_episode(self, episode_id: int) -> FileMapping | None:
        return self.get_session().query(FileMapping).filter_by(episode_id=episode_id).first()
