import os
import pytest

# Configure environment variables before importing the FastAPI app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TMDB_API_KEY"] = "test_key"
os.environ["TORRSERVER_BASE_URL"] = "http://test_torr:8090"

from fastapi.testclient import TestClient
from stremio_catalog_provider.api import app
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.entity.media_item import MediaItem
from stremio_catalog_provider.entity.torrent import Torrent
from stremio_catalog_provider.entity.file_mapping import FileMapping
from stremio_catalog_provider.manager.db_manager import DbManager

def test_stremio_endpoints() -> None:
    """Tests all public Stremio routes: manifest, catalog, meta, and stream."""
    # Build database schema
    container = DefaultContainer.getInstance()
    db_manager = container.get(DbManager)
    BaseEntity.metadata.create_all(db_manager.engine)

    # Insert mock data
    session = db_manager.get_session()

    media = MediaItem(imdb_id="tt99999", type="movie", title="FastAPI Movie", year=2026)
    session.add(media)
    session.commit()

    torrent = Torrent(
        info_hash="hash123", magnet_url="magnet:?xt=urn:btih:hash123", status="PROCESSED"
    )
    session.add(torrent)
    session.commit()

    mapping = FileMapping(
        torrent_hash="hash123",
        file_index=0,
        file_path="movie.mp4",
        file_size=2000000000,
        media_item_id=media.id
    )
    session.add(mapping)
    session.commit()

    client = TestClient(app)

    # 1. Test Manifest
    res_manifest = client.get("/manifest.json")
    assert res_manifest.status_code == 200
    assert res_manifest.json()["id"] == "org.stremio.custom.catalog"

    # 2. Test Catalog
    res_catalog = client.get("/catalog/movie/custom_movies.json")
    assert res_catalog.status_code == 200
    assert len(res_catalog.json()["metas"]) == 1
    assert res_catalog.json()["metas"][0]["id"] == "tt99999"

    # 3. Test Meta
    res_meta = client.get("/meta/movie/tt99999.json")
    assert res_meta.status_code == 200
    assert res_meta.json()["meta"]["name"] == "FastAPI Movie"

    # 4. Test Stream
    res_stream = client.get("/stream/movie/tt99999.json")
    assert res_stream.status_code == 200
    assert len(res_stream.json()["streams"]) == 1
    assert "movie.mp4" in res_stream.json()["streams"][0]["title"]
