from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.entity.file_mapping import FileMapping

def test_create_tables_and_torrent_record() -> None:
    engine = create_engine("sqlite:///:memory:")
    BaseEntity.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    torrent = Torrent(
        info_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
        magnet_url="magnet:?xt=urn:btih:1a2b3c...",
        title="Test Torrent",
        status="QUEUED"
    )
    session.add(torrent)
    session.commit()

    saved = session.query(Torrent).filter_by(
        info_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t"
    ).first()
    assert saved is not None
    assert saved.title == "Test Torrent"
    assert saved.status == "QUEUED"


def test_torrent_id_relationship() -> None:
    engine = create_engine("sqlite:///:memory:")
    BaseEntity.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Creazione Torrent
    torrent = Torrent(
        info_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
        magnet_url="magnet:?xt=urn:btih:1a2b3c...",
        title="Test Torrent"
    )
    session.add(torrent)
    session.commit()

    assert torrent.id is not None  # Deve avere un ID numerico autoincrementale

    # Creazione FileMapping associato
    mapping = FileMapping(
        torrent_id=torrent.id,
        file_index=0,
        file_path="video.mkv",
        file_size=1000000,
        manually_corrected=False
    )
    session.add(mapping)
    session.commit()

    assert mapping.torrent_hash == "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t"

