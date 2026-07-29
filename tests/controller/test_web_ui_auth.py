import os
import base64

# Configure environment variables before importing the FastAPI app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TMDB_API_KEY"] = "test_key"
os.environ["TORRSERVER_BASE_URL"] = "http://test_torr:8090"
os.environ["BASIC_AUTH_USERNAME"] = "test_user"
os.environ["BASIC_AUTH_PASSWORD"] = "test_pass"

from fastapi.testclient import TestClient
from stremio_catalog_provider.api import app
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.config.web_ui_config import WebUiConfig
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.manager.db_manager import DbManager


def test_web_ui_and_api_auth_denied() -> None:
    """Verifies that routes require HTTP Basic Authentication and deny unauthorized requests."""
    container = DefaultContainer.getInstance()
    ui_config = container.get(WebUiConfig)
    ui_config.username = "test_user"
    ui_config.password = "test_pass"

    db_manager = container.get(DbManager)
    BaseEntity.metadata.create_all(db_manager.engine)

    client = TestClient(app)

    # 1. Test UI route (/dashboard) without auth header
    res_ui = client.get("/dashboard")
    assert res_ui.status_code == 401
    assert "WWW-Authenticate" in res_ui.headers

    # 2. Test API route (/api/torrents) without auth header
    res_api = client.post("/api/torrents", json={"magnet_url": "dummy"})
    assert res_api.status_code == 401


def test_web_ui_and_api_auth_allowed() -> None:
    """Verifies that correct credentials grant access while incorrect credentials deny access."""
    container = DefaultContainer.getInstance()
    ui_config = container.get(WebUiConfig)
    ui_config.username = "test_user"
    ui_config.password = "test_pass"

    db_manager = container.get(DbManager)
    BaseEntity.metadata.create_all(db_manager.engine)

    client = TestClient(app)

    # Setup basic auth header with correct credentials
    token = base64.b64encode(b"test_user:test_pass").decode("utf-8")
    headers = {"Authorization": f"Basic {token}"}

    # 1. Test UI route (/dashboard) with correct credentials
    res_ui = client.get("/dashboard", headers=headers)
    assert res_ui.status_code == 200

    # 2. Test UI route (/dashboard) with incorrect credentials
    wrong_token = base64.b64encode(b"wrong_user:wrong_pass").decode("utf-8")
    wrong_headers = {"Authorization": f"Basic {wrong_token}"}
    res_ui_wrong = client.get("/dashboard", headers=wrong_headers)
    assert res_ui_wrong.status_code == 401


def test_update_torrent_endpoint() -> None:
    container = DefaultContainer.getInstance()
    ui_config = container.get(WebUiConfig)
    ui_config.username = "test_user"
    ui_config.password = "test_pass"

    db_manager = container.get(DbManager)
    BaseEntity.metadata.create_all(db_manager.engine)
    session = db_manager.get_session()

    from stremio_catalog_provider.entity.media_item import MediaItem
    from stremio_catalog_provider.entity.torrent import Torrent
    from stremio_catalog_provider.entity.file_mapping import FileMapping

    media = MediaItem(
        id=10, imdb_id="ttMovie", type="movie", title="Movie Test", year=2026
    )
    session.add(media)

    torrent = Torrent(
        info_hash="hashupdate",
        magnet_url="magnetupdate",
        title="Original Title",
        status="QUEUED",
    )
    session.add(torrent)
    session.commit()

    mapping = FileMapping(
        torrent_id=torrent.id, file_index=1, file_path="movie.mkv", file_size=1000
    )
    session.add(mapping)
    session.commit()

    client = TestClient(app)
    token = base64.b64encode(b"test_user:test_pass").decode("utf-8")
    headers = {"Authorization": f"Basic {token}"}

    payload = {"title": "New Title", "media_id": 10, "remap_files": True}

    # Verify authentication is required
    response_no_auth = client.put(f"/api/torrents/{torrent.id}", json=payload)
    assert response_no_auth.status_code == 401

    # Update torrent and mapping
    response = client.put(f"/api/torrents/{torrent.id}", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify changes in DB
    session.expire_all()
    updated_torrent = session.query(Torrent).filter_by(id=torrent.id).first()
    assert updated_torrent.title == "New Title"
    assert updated_torrent.media_id == 10

    updated_mapping = session.query(FileMapping).filter_by(id=mapping.id).first()
    assert updated_mapping.media_item_id == 10
