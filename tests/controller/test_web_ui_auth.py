import os
import base64
import pytest

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
