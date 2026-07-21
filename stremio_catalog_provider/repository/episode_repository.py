from injector import inject
from sqlalchemy.orm import Session
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.manager.db_manager import DbManager

class EpisodeRepository:
    """Repository class for Episode entity database operations."""

    @inject
    def __init__(self, db_manager: DbManager) -> None:
        self.db_manager = db_manager

    def get_session(self) -> Session:
        return self.db_manager.get_session()

    def get_or_create(self, media_item_id: int, season: int, episode_num: int) -> Episode:
        session = self.get_session()
        episode = session.query(Episode).filter_by(
            media_item_id=media_item_id, season=season, episode=episode_num
        ).first()
        if not episode:
            episode = Episode(media_item_id=media_item_id, season=season, episode=episode_num)
            session.add(episode)
            session.commit()
        return episode
