from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
# Import all entities to register them in SQLAlchemy metadata registry
from stremio_catalog_provider.entity import BaseEntity, Torrent, MediaItem, Episode, FileMapping

class DbManager:
    """Manager for database engine and session factory."""

    def __init__(self, db_url: str) -> None:
        if "sqlite" in db_url:
            from sqlalchemy.pool import StaticPool
            self.engine: Engine = create_engine(
                db_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False}
            )
        else:
            self.engine: Engine = create_engine(db_url, pool_recycle=3600)
        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session = scoped_session(self.session_factory)

    def get_session(self) -> Session:
        return self.scoped_session()
