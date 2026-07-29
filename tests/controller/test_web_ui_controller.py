from unittest.mock import MagicMock
from fastapi import Request
from stremio_catalog_provider.controller.web_ui_controller import WebUiController
from stremio_catalog_provider.config.app_config import AppConfig
from stremio_catalog_provider.config.web_ui_config import WebUiConfig


def test_dashboard_uses_configured_base_url():
    # Mock dependencies
    torrent_repo = MagicMock()
    torrent_repo.get_all.return_value = []
    media_repo = MagicMock()
    media_repo.search_local.return_value = []
    templates = MagicMock()
    app_config = AppConfig(base_url="https://public-host.com")
    ui_config = WebUiConfig(username="admin", password="password")

    controller = WebUiController(
        config=ui_config,
        app_config=app_config,
        media_repo=media_repo,
        torrent_repo=torrent_repo,
        mapping_repo=MagicMock(),
        episode_repo=MagicMock(),
    )
    controller.templates = templates

    request = MagicMock(spec=Request)
    request.base_url = "http://localhost:8000"

    credentials = MagicMock()
    controller.verify_credentials = MagicMock()

    import asyncio

    asyncio.run(controller.dashboard(request=request, credentials=credentials))

    # Verify that templates.TemplateResponse was called with public base_url
    args, kwargs = templates.TemplateResponse.call_args
    context = args[2]
    assert context["stremio_url"] == "https://public-host.com/manifest.json"
