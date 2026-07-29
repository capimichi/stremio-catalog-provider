from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.config.app_config import AppConfig


def test_container_binds_app_config():
    container = DefaultContainer.getInstance()
    app_config = container.get(AppConfig)
    assert isinstance(app_config, AppConfig)
