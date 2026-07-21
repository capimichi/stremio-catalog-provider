import pytest
from unittest.mock import MagicMock
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.entity.episode import Episode
from stremio_catalog_provider.entity.file_mapping import FileMapping
from stremio_catalog_provider.manager.db_manager import DbManager
from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
from stremio_catalog_provider.client.tmdb_client import TMDbClient
from stremio_catalog_provider.repository.torrent_repository import TorrentRepository
from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
from stremio_catalog_provider.repository.episode_repository import EpisodeRepository
from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
from stremio_catalog_provider.service.torrent_parser_service import TorrentParserService
from stremio_catalog_provider.service.torrent_service import TorrentService
from stremio_catalog_provider.service.media_item_service import MediaItemService
from stremio_catalog_provider.service.file_mapping_service import FileMappingService
from stremio_catalog_provider.service.stremio_service import StremioService

def test_torrent_parser_service() -> None:
    parser = TorrentParserService()
    res = parser.parse_filename("The.Simpsons.S01E03.1080p.mkv")
    assert res["title"] == "The Simpsons"
    assert res["season"] == 1
    assert res["episode"] == 3

def test_torrent_service_add() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)
    repo = TorrentRepository(db_manager)
    service = TorrentService(repo)

    magnet = "magnet:?xt=urn:btih:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b&dn=Test"
    torrent = service.add_torrent(magnet, media_id=42)

    assert torrent.info_hash == "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
    assert torrent.predefined_media_item_id == 42
    assert torrent.status == "QUEUED"

    again = service.add_torrent(magnet, media_id=99)
    assert again.info_hash == "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
    assert again.predefined_media_item_id == 42

def test_media_item_service_add() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)
    repo = MediaItemRepository(db_manager)

    mock_tmdb = MagicMock(spec=TMDbClient)
    mock_tmdb.get_details.return_value = {
        "external_ids": {"imdb_id": "tt0123456"},
        "title": "A Movie Story",
        "release_date": "2026-12-25",
        "overview": "A movie description",
        "poster_path": "/poster.jpg",
        "backdrop_path": "/backdrop.jpg"
    }

    service = MediaItemService(repo, mock_tmdb)
    media = service.add_media_from_tmdb(12345, "movie")

    assert media.imdb_id == "tt0123456"
    assert media.title == "A Movie Story"
    assert media.year == 2026
    assert media.type == "movie"
    assert media.poster_url == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert media.background_url == "https://image.tmdb.org/t/p/original/backdrop.jpg"

def test_file_mapping_service_remap() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)

    session = db_manager.get_session()
    torrent = Torrent(info_hash="hash123", magnet_url="magnet123")
    media = MediaItem(id=77, imdb_id="tt99999", type="series", title="Test TV Show")
    session.add(torrent)
    session.add(media)
    session.commit()

    mapping = FileMapping(
        id=1,
        torrent_hash="hash123",
        file_index=0,
        file_path="S1E2.mkv",
        file_size=1000,
        media_item_id=77
    )
    session.add(mapping)
    session.commit()

    mapping_repo = FileMappingRepository(db_manager)
    episode_repo = EpisodeRepository(db_manager)
    service = FileMappingService(mapping_repo, episode_repo)

    service.remap_file(mapping_id=1, episode_num=2, season_num=1)

    updated_mapping = session.query(FileMapping).filter_by(id=1).first()
    assert updated_mapping is not None
    assert updated_mapping.manually_corrected is True
    assert updated_mapping.episode_id is not None

    episode = session.query(Episode).filter_by(id=updated_mapping.episode_id).first()
    assert episode is not None
    assert episode.season == 1
    assert episode.episode == 2

def test_stremio_service() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)

    session = db_manager.get_session()
    media_movie = MediaItem(imdb_id="ttMovie", type="movie", title="Movie Test", year=2026)
    media_series = MediaItem(imdb_id="ttSeries", type="series", title="Series Test", year=2025)
    session.add(media_movie)
    session.add(media_series)
    session.commit()

    torrent = Torrent(info_hash="hash123", magnet_url="magnet123")
    session.add(torrent)
    session.commit()

    mapping_movie = FileMapping(
        torrent_hash="hash123",
        file_index=0,
        file_path="movie.mkv",
        file_size=1000 * 1024 * 1024,
        media_item_id=media_movie.id
    )
    session.add(mapping_movie)
    session.commit()

    media_repo = MediaItemRepository(db_manager)
    mapping_repo = FileMappingRepository(db_manager)
    torr_config = TorrServerConfig("http://local:8090")

    service = StremioService(media_repo, mapping_repo, torr_config)

    manifest = service.get_manifest()
    assert manifest["id"] == "org.stremio.custom.catalog"

    movie_catalog = service.get_catalog("movie")
    assert len(movie_catalog["metas"]) == 1
    assert movie_catalog["metas"][0]["id"] == "ttMovie"

    movie_meta = service.get_meta("movie", "ttMovie")
    assert movie_meta["meta"]["id"] == "ttMovie"

    movie_stream = service.get_stream("movie", "ttMovie")
    assert len(movie_stream["streams"]) == 1
    assert "movie.mkv" in movie_stream["streams"][0]["title"]
    assert "link=0" in movie_stream["streams"][0]["url"]
    assert "hash=hash123" in movie_stream["streams"][0]["url"]
