from __future__ import annotations
import os
from typing import Type, TypeVar
from dotenv import load_dotenv
from injector import Injector
from stremio_catalog_provider.config.tmdb_config import TMDbConfig
from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
from stremio_catalog_provider.config.web_ui_config import WebUiConfig
from stremio_catalog_provider.manager.db_manager import DbManager

T = TypeVar("T")

class DefaultContainer:
    """Dependency injection container using the injector library."""

    instance: DefaultContainer | None = None

    @staticmethod
    def getInstance() -> DefaultContainer:
        if DefaultContainer.instance is None:
            DefaultContainer.instance = DefaultContainer()
        return DefaultContainer.instance

    def __init__(self) -> None:
        self.injector = Injector()
        load_dotenv()
        self._init_bindings()

    def get(self, key: Type[T]) -> T:
        return self.injector.get(key)

    def _init_bindings(self) -> None:
        db_url = os.environ.get("DATABASE_URL", "mysql+pymysql://catalog_user:catalog_password@db/stremio_catalog")
        tmdb_key = os.environ.get("TMDB_API_KEY", "")
        torr_url = os.environ.get("TORRSERVER_BASE_URL", "http://localhost:8090")
        torr_user = os.environ.get("TORRSERVER_USERNAME")
        torr_pass = os.environ.get("TORRSERVER_PASSWORD")
        ui_user = os.environ.get("BASIC_AUTH_USERNAME", "admin")
        ui_pass = os.environ.get("BASIC_AUTH_PASSWORD", "admin")

        self.injector.binder.bind(DbManager, to=DbManager(db_url))
        self.injector.binder.bind(TMDbConfig, to=TMDbConfig(tmdb_key))
        self.injector.binder.bind(TorrServerConfig, to=TorrServerConfig(torr_url, torr_user, torr_pass))
        self.injector.binder.bind(WebUiConfig, to=WebUiConfig(ui_user, ui_pass))
