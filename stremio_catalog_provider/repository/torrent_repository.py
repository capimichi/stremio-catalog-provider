from typing import Optional
from injector import inject
from sqlalchemy.orm import Session
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.manager.db_manager import DbManager

class TorrentRepository:
    """Repository class for Torrent entity database operations."""

    @inject
    def __init__(self, db_manager: DbManager) -> None:
        self.db_manager = db_manager

    def get_session(self) -> Session:
        return self.db_manager.get_session()

    def add(self, torrent: Torrent) -> None:
        session = self.get_session()
        session.add(torrent)
        session.commit()

    def get_by_hash(self, info_hash: str) -> Torrent | None:
        return self.get_session().query(Torrent).filter_by(info_hash=info_hash).first()

    def get_all(self) -> list[Torrent]:
        return self.get_session().query(Torrent).order_by(Torrent.added_at.desc()).all()

    def delete(self, info_hash: str) -> None:
        session = self.get_session()
        torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
        if torrent:
            session.delete(torrent)
            session.commit()

    def get_next_queued_for_update(self) -> Optional[Torrent]:
        """Retrieves and locks the next QUEUED torrent, changing its status to PROCESSING."""
        session = self.get_session()
        try:
            query = session.query(Torrent).filter(Torrent.status == "QUEUED").order_by(Torrent.added_at.asc())

            # Attempt to extract with skip locked if supported (MySQL/MariaDB)
            if session.bind.dialect.name in ("mysql", "mariadb"):
                query = query.with_for_update(skip_locked=True)

            torrent = query.first()
            if torrent:
                torrent.status = "PROCESSING"
                session.commit()
            else:
                session.rollback()
            return torrent
        except Exception:
            session.rollback()
            raise
