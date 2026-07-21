from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.entity.file_mapping import FileMapping
from stremio_catalog_provider.manager.db_manager import DbManager
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository

def test_get_next_queued_for_update() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)
    repo = TorrentRepository(db_manager)

    t1 = Torrent(info_hash="hash1", magnet_url="magnet1", title="T1", status="QUEUED")
    t2 = Torrent(info_hash="hash2", magnet_url="magnet2", title="T2", status="QUEUED")

    repo.add(t1)
    repo.add(t2)

    first = repo.get_next_queued_for_update()
    assert first is not None
    assert first.info_hash == "hash1"
    assert first.status == "PROCESSING"
