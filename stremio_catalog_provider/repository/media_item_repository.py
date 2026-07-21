from injector import inject
from sqlalchemy.orm import Session
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.manager.db_manager import DbManager

class MediaItemRepository:
    """Repository class for MediaItem entity database operations."""

    @inject
    def __init__(self, db_manager: DbManager) -> None:
        self.db_manager = db_manager

    def get_session(self) -> Session:
        return self.db_manager.get_session()

    def add(self, media_item: MediaItem) -> None:
        session = self.get_session()
        session.add(media_item)
        session.commit()

    def get_by_id(self, id: int) -> MediaItem | None:
        return self.get_session().query(MediaItem).filter_by(id=id).first()

    def get_by_imdb_id(self, imdb_id: str) -> MediaItem | None:
        return self.get_session().query(MediaItem).filter_by(imdb_id=imdb_id).first()

    def search_local(self, query: str, media_type: str | None = None) -> list[MediaItem]:
        session = self.get_session()
        q = session.query(MediaItem)
        if query:
            q = q.filter(MediaItem.title.like(f"%{query}%"))
        if media_type:
            q = q.filter(MediaItem.type == media_type)
        return q.all()
