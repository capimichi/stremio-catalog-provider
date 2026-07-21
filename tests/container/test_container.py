import os
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.config.tmdb_config import TMDbConfig
from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
from stremio_catalog_provider.manager.db_manager import DbManager

def test_container_resolves_bindings() -> None:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["TMDB_API_KEY"] = "test_key"
    os.environ["TORRSERVER_BASE_URL"] = "http://test_torr:8090"

    container = DefaultContainer()

    db_manager = container.get(DbManager)
    tmdb_config = container.get(TMDbConfig)
    torr_config = container.get(TorrServerConfig)

    assert db_manager is not None
    assert tmdb_config.api_key == "test_key"
    assert torr_config.base_url == "http://test_torr:8090"
