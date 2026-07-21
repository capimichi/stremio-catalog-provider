import pytest
from unittest.mock import MagicMock
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.entity.file_mapping import FileMapping
from stremio_catalog_provider.manager.db_manager import DbManager
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.repository.episode_repository import EpisodeRepository
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.client.torrserver_client import TorrServerClient
from stremio_catalog_provider.client.tmdb_client import TMDbClient
from stremio_catalog_provider.service.torrent_parser_service import TorrentParserService
from stremio_catalog_provider.service.media_item_service import MediaItemService
from stremio_catalog_provider.service.torrent_process_service import TorrentProcessService

def test_process_next_torrent_with_predefined_media_item() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)

    session = db_manager.get_session()
    media = MediaItem(id=55, imdb_id="ttPredefined", type="movie", title="Predefined Movie")
    session.add(media)
    session.commit()

    torrent = Torrent(
        info_hash="hash123",
        magnet_url="magnet:?xt=urn:btih:hash123",
        status="QUEUED",
        predefined_media_item_id=55
    )
    session.add(torrent)
    session.commit()

    torrent_repo = TorrentRepository(db_manager)
    media_repo = MediaItemRepository(db_manager)
    episode_repo = EpisodeRepository(db_manager)
    mapping_repo = FileMappingRepository(db_manager)

    mock_torr = MagicMock(spec=TorrServerClient)
    mock_torr.add_torrent.return_value = "hash123"
    mock_torr.get_torrent_files.return_value = [{"id": 0, "path": "movie.mp4", "size": 123456}]

    mock_tmdb = MagicMock(spec=TMDbClient)
    parser_service = TorrentParserService()
    mock_media_item_service = MagicMock(spec=MediaItemService)

    process_service = TorrentProcessService(
        torrent_repo=torrent_repo,
        media_repo=media_repo,
        episode_repo=episode_repo,
        mapping_repo=mapping_repo,
        torr_client=mock_torr,
        tmdb_client=mock_tmdb,
        parser_service=parser_service,
        media_item_service=mock_media_item_service
    )

    success = process_service.process_next_torrent(poll_timeout=1.0, poll_interval=0.1)
    assert success is True

    processed_torrent = session.query(Torrent).filter_by(info_hash="hash123").first()
    assert processed_torrent is not None
    assert processed_torrent.status == "PROCESSED"
    assert processed_torrent.processed_at is not None

    mappings = session.query(FileMapping).filter_by(torrent_hash="hash123").all()
    assert len(mappings) == 1
    assert mappings[0].media_item_id == 55
    assert mappings[0].file_path == "movie.mp4"

def test_process_next_torrent_auto_tmdb_search() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)

    session = db_manager.get_session()
    torrent = Torrent(
        info_hash="hash456", magnet_url="magnet:?xt=urn:btih:hash456", status="QUEUED"
    )
    session.add(torrent)
    session.commit()

    torrent_repo = TorrentRepository(db_manager)
    media_repo = MediaItemRepository(db_manager)
    episode_repo = EpisodeRepository(db_manager)
    mapping_repo = FileMappingRepository(db_manager)

    mock_torr = MagicMock(spec=TorrServerClient)
    mock_torr.add_torrent.return_value = "hash456"
    mock_torr.get_torrent_files.return_value = [
        {"id": 1, "path": "The.Matrix.1999.mkv", "size": 987654}
    ]

    mock_tmdb = MagicMock(spec=TMDbClient)
    mock_tmdb.search_media.return_value = [{"id": 603, "title": "The Matrix"}]

    parser_service = TorrentParserService()

    resolved_media = MediaItem(
        id=99, imdb_id="tt0133093", type="movie", title="The Matrix", year=1999
    )
    mock_media_item_service = MagicMock(spec=MediaItemService)
    mock_media_item_service.add_media_from_tmdb.return_value = resolved_media

    session.add(resolved_media)
    session.commit()

    process_service = TorrentProcessService(
        torrent_repo=torrent_repo,
        media_repo=media_repo,
        episode_repo=episode_repo,
        mapping_repo=mapping_repo,
        torr_client=mock_torr,
        tmdb_client=mock_tmdb,
        parser_service=parser_service,
        media_item_service=mock_media_item_service
    )

    success = process_service.process_next_torrent(poll_timeout=1.0, poll_interval=0.1)
    assert success is True

    processed_torrent = session.query(Torrent).filter_by(info_hash="hash456").first()
    assert processed_torrent is not None
    assert processed_torrent.status == "PROCESSED"

    mock_tmdb.search_media.assert_called_once_with("The Matrix", "movie", 1999)
    mock_media_item_service.add_media_from_tmdb.assert_called_once_with(603, "movie")

    mappings = session.query(FileMapping).filter_by(torrent_hash="hash456").all()
    assert len(mappings) == 1
    assert mappings[0].media_item_id == 99

def test_process_next_torrent_timeout_failure() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)

    session = db_manager.get_session()
    torrent = Torrent(
        info_hash="hash789", magnet_url="magnet:?xt=urn:btih:hash789", status="QUEUED"
    )
    session.add(torrent)
    session.commit()

    torrent_repo = TorrentRepository(db_manager)
    media_repo = MediaItemRepository(db_manager)
    episode_repo = EpisodeRepository(db_manager)
    mapping_repo = FileMappingRepository(db_manager)

    mock_torr = MagicMock(spec=TorrServerClient)
    mock_torr.add_torrent.return_value = "hash789"
    mock_torr.get_torrent_files.return_value = []

    mock_tmdb = MagicMock(spec=TMDbClient)
    parser_service = TorrentParserService()
    mock_media_item_service = MagicMock(spec=MediaItemService)

    process_service = TorrentProcessService(
        torrent_repo=torrent_repo,
        media_repo=media_repo,
        episode_repo=episode_repo,
        mapping_repo=mapping_repo,
        torr_client=mock_torr,
        tmdb_client=mock_tmdb,
        parser_service=parser_service,
        media_item_service=mock_media_item_service
    )

    success = process_service.process_next_torrent(poll_timeout=0.2, poll_interval=0.1)
    assert success is True

    processed_torrent = session.query(Torrent).filter_by(info_hash="hash789").first()
    assert processed_torrent is not None
    assert processed_torrent.status == "FAILED"
    assert (
        "timeout" in processed_torrent.error_message.lower()
        or "did not resolve" in processed_torrent.error_message.lower()
    )
    mock_torr.remove_torrent.assert_called_once_with("hash789")
