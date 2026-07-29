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
from stremio_catalog_provider.repository.media_item_repository import (
    MediaItemRepository,
)
from stremio_catalog_provider.repository.episode_repository import EpisodeRepository
from stremio_catalog_provider.repository.file_mapping_repository import (
    FileMappingRepository,
)
from stremio_catalog_provider.service.torrent_parser_service import TorrentParserService
from stremio_catalog_provider.service.torrent_service import TorrentService
from stremio_catalog_provider.service.media_item_service import MediaItemService
from stremio_catalog_provider.service.file_mapping_service import FileMappingService
from stremio_catalog_provider.service.stremio_service import StremioService


def test_torrent_parser_service() -> None:
    from stremio_catalog_provider.config.app_config import AppConfig

    config = AppConfig(supported_languages="ita,eng,deu")
    parser = TorrentParserService(config)

    # Standard PTN resolution extraction
    res1 = parser.parse_filename("The.Simpsons.S01E03.1080p.mkv")
    assert res1["title"] == "The Simpsons"
    assert res1["season"] == 1
    assert res1["episode"] == 3
    assert res1["resolution"] == "1080p"

    # Fallback resolution detection
    res2 = parser.parse_filename("MyMovie.1080.x264.mkv")
    assert res2["resolution"] == "1080p"

    # Configured language detection (Italian)
    res3 = parser.parse_filename("Dune.Parte.Due.2024.Italiano.H264.mkv")
    assert res3["languages"] == "ita"

    # Dual language detection
    res4 = parser.parse_filename("Dune.Parte.Due.2024.ita.eng.H264.mkv")
    assert "ita" in res4["languages"]
    assert "eng" in res4["languages"]

    # Multi/Dual fallback detection
    res5 = parser.parse_filename("Dune.Part.2.Dual.Audio.mkv")
    assert res5["languages"] == "multi"


def test_torrent_service_add() -> None:
    db_manager = DbManager("sqlite:///:memory:")
    BaseEntity.metadata.create_all(db_manager.engine)
    repo = TorrentRepository(db_manager)
    service = TorrentService(repo)

    magnet = "magnet:?xt=urn:btih:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b&dn=Test"
    torrent = service.add_torrent(magnet, media_id=42)

    assert torrent.info_hash == "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
    assert torrent.media_id == 42
    assert torrent.status == "QUEUED"

    again = service.add_torrent(magnet, media_id=99)
    assert again.info_hash == "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
    assert again.media_id == 42


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
        "backdrop_path": "/backdrop.jpg",
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
        torrent_id=torrent.id,
        file_index=1,
        file_path="S1E2.mkv",
        file_size=1000,
        media_item_id=77,
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
    media_movie = MediaItem(
        imdb_id="ttMovie", type="movie", title="Movie Test", year=2026
    )
    media_series = MediaItem(
        imdb_id="ttSeries", type="series", title="Series Test", year=2025
    )
    session.add(media_movie)
    session.add(media_series)
    session.commit()

    torrent = Torrent(
        info_hash="hash123",
        magnet_url="magnet123",
        resolution="1080p",
        quality="BluRay",
        codec="x265",
        audio="AC3",
        languages="ita,eng",
    )
    session.add(torrent)
    session.commit()

    mapping_movie = FileMapping(
        torrent_id=torrent.id,
        file_index=1,
        file_path="movie.mkv",
        file_size=1000 * 1024 * 1024,
        media_item_id=media_movie.id,
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
    stream = movie_stream["streams"][0]
    assert stream["name"] == "Catalog Provider\n1080p"
    assert "📄 movie.mkv" in stream["description"]
    assert "💾 0.98 GB" in stream["description"]
    assert "⚙️ BLURAY | X265 | AC3 | 🇮🇹 🇬🇧" in stream["description"]
    assert stream["infoHash"] == "hash123"
    assert stream["fileIdx"] == 0
