import os
import base64
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TMDB_API_KEY"] = "test_key"
os.environ["TORRSERVER_BASE_URL"] = "http://test_torr:8090"
os.environ["BASIC_AUTH_USERNAME"] = "test_user"
os.environ["BASIC_AUTH_PASSWORD"] = "test_pass"

from stremio_catalog_provider.api import app
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.manager.db_manager import DbManager

def test_torrents_page_elements_and_layout() -> None:
    container = DefaultContainer.getInstance()
    db_manager = container.get(DbManager)
    BaseEntity.metadata.create_all(db_manager.engine)
    session = db_manager.get_session()

    from stremio_catalog_provider.entity.torrent import Torrent
    
    # Aggiunge un torrent mock per popolare la tabella
    torrent = Torrent(
        info_hash="1234567890abcdef1234567890abcdef12345678",
        magnet_url="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
        title="Test Torrent Title That Is Extremely Long to Test Truncation",
        status="FAILED"
    )
    session.add(torrent)
    session.commit()

    client = TestClient(app)
    token = base64.b64encode(b"test_user:test_pass").decode("utf-8")
    headers = {"Authorization": f"Basic {token}"}

    res = client.get("/torrents", headers=headers)
    assert res.status_code == 200
    html = res.text

    # Verifica FontAwesome CDN
    assert "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" in html

    # Verifica struttura tabella responsive
    assert "class=\"table-responsive\"" in html

    # Verifica classi colonne
    assert "class=\"col-title\"" in html
    assert "class=\"col-hash\"" in html
    assert "class=\"col-actions\"" in html

    # Verifica icone FontAwesome presenti nei pulsanti
    assert "fa-rotate-right" in html
    assert "fa-pen-to-square" in html
    assert "fa-folder-open" in html
    assert "fa-trash-can" in html
