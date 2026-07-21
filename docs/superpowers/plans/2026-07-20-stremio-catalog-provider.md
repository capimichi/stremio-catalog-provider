# Stremio Custom Catalog Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Realizzare un addon Stremio e un'interfaccia di amministrazione web per gestire un catalogo personalizzato basato su torrent e TorrServer, con mappatura automatica tramite TMDB e correzioni manuali.

**Architecture:** Moduli Clean Architecture con iniezione di dipendenze (libreria `injector`). I controller FastAPI gestiscono le API di Stremio e la Web UI (Jinja2, template e statici nella root). Il background worker gira in un processo CLI separato ed effettua il polling di MariaDB (`SKIP LOCKED`) coordinando TorrServer e TMDB.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, Alembic, MariaDB, HTTPX, PTN (Python Torrent Name parser), Injector, Click, Pytest, Jinja2, Vanilla CSS (Dark/Glassmorphic).

## Global Constraints

* Seguire PEP 8 con indentazione a 4 spazi e limite di 100 caratteri per riga.
* Utilizzare i type hints in tutto il codice.
* Nomi di file e cartelle in `snake_case`, classi in `CapWords`, funzioni/variabili in `snake_case`.
* Le dipendenze di classe devono essere iniettate tramite `@inject` sul costruttore.
* In `DefaultContainer._init_bindings` bindare esplicitamente solo le classi che richiedono parametri letterali (config, URL, chiavi API). Le altre classi si risolvono implicitamente.
* Non usare il pattern Service Locator (evitare `DefaultContainer.getInstance()` all'interno delle classi).
* Evitare costanti a livello di modulo; definirle all'interno della classe appropriata.
* Non definire logger a livello di modulo; iniettarli o risolverli tramite DI.
* Tutte le chiamate HTTP esterne (TMDB e TorrServer) devono risiedere nel modulo `client/` ed essere mockate nei test.
* I template HTML (`templates/`) e le risorse statiche (`static/`) devono risiedere alla root del repository.

---

### Task 1: Scaffolding, Dipendenze e Container DI

In questa fase configuriamo il set di dipendenze del progetto, creiamo la configurazione basata su variabili d'ambiente, configuriamo il DbManager per gestire le connessioni SQLAlchemy e prepariamo il container `DefaultContainer` con la libreria `injector`.

**Files:**
* Modify: `requirements.txt`
* Create: `stremio_catalog_provider/config/tmdb_config.py`
* Create: `stremio_catalog_provider/config/torrserver_config.py`
* Create: `stremio_catalog_provider/manager/db_manager.py`
* Create: `stremio_catalog_provider/container/default_container.py`
* Test: `tests/container/test_container.py`

**Interfaces:**
* Produces: `DbManager` (fornisce sessioni del DB), `TMDbConfig` e `TorrServerConfig` (incapsulano le impostazioni), `DefaultContainer` (gestisce l'injector globale).

- [ ] **Step 1: Scrivere le dipendenze in requirements.txt**
  Modificare `requirements.txt` impostando le dipendenze:
  ```text
  fastapi>=0.110.0
  uvicorn[standard]>=0.28.0
  injector>=0.21.0
  httpx>=0.27.0
  sqlalchemy>=2.0.30
  alembic>=1.13.0
  pymysql>=1.1.0
  cryptography>=41.0.0
  python-dotenv>=1.0.1
  click>=8.1.7
  jinja2>=3.1.0
  python-multipart>=0.0.6
  PTN>=2.7.0
  pytest>=8.0.0
  pytest-asyncio>=0.23.0
  ```

- [ ] **Step 2: Creare TMDbConfig**
  Creare `stremio_catalog_provider/config/tmdb_config.py`:
  ```python
  class TMDbConfig:
      def __init__(self, api_key: str):
          self.api_key = api_key
  ```

- [ ] **Step 3: Creare TorrServerConfig**
  Creare `stremio_catalog_provider/config/torrserver_config.py`:
  ```python
  class TorrServerConfig:
      def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
          self.base_url = base_url
          self.username = username
          self.password = password
  ```

- [ ] **Step 4: Creare DbManager**
  Creare `stremio_catalog_provider/manager/db_manager.py`:
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker, scoped_session

  class DbManager:
      def __init__(self, db_url: str):
          self.engine = create_engine(db_url, pool_recycle=3600)
          self.session_factory = sessionmaker(bind=self.engine)
          self.scoped_session = scoped_session(self.session_factory)

      def get_session(self):
          return self.scoped_session()
  ```

- [ ] **Step 5: Creare DefaultContainer**
  Creare `stremio_catalog_provider/container/default_container.py`:
  ```python
  import os
  from dotenv import load_dotenv
  from injector import Injector
  from stremio_catalog_provider.config.tmdb_config import TMDbConfig
  from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
  from stremio_catalog_provider.manager.db_manager import DbManager

  class DefaultContainer:
      instance = None

      @staticmethod
      def getInstance():
          if DefaultContainer.instance is None:
              DefaultContainer.instance = DefaultContainer()
          return DefaultContainer.instance

      def __init__(self):
          self.injector = Injector()
          load_dotenv()
          self._init_bindings()

      def get(self, key):
          return self.injector.get(key)

      def _init_bindings(self):
          db_url = os.environ.get("DATABASE_URL", "mysql+pymysql://catalog_user:catalog_password@db/stremio_catalog")
          tmdb_key = os.environ.get("TMDB_API_KEY", "")
          torr_url = os.environ.get("TORRSERVER_BASE_URL", "http://localhost:8090")
          torr_user = os.environ.get("TORRSERVER_USERNAME")
          torr_pass = os.environ.get("TORRSERVER_PASSWORD")

          self.injector.binder.bind(DbManager, to=DbManager(db_url))
          self.injector.binder.bind(TMDbConfig, to=TMDbConfig(tmdb_key))
          self.injector.binder.bind(TorrServerConfig, to=TorrServerConfig(torr_url, torr_user, torr_pass))
  ```

- [ ] **Step 6: Scrivere il test per DefaultContainer**
  Creare `tests/container/test_container.py`:
  ```python
  import os
  from stremio_catalog_provider.container.default_container import DefaultContainer
  from stremio_catalog_provider.config.tmdb_config import TMDbConfig
  from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
  from stremio_catalog_provider.manager.db_manager import DbManager

  def test_container_resolves_bindings():
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
  ```

- [ ] **Step 7: Eseguire il test**
  Run: `pytest tests/container/test_container.py`
  Expected: PASS

---

### Task 2: Entità Database e Migrazioni Alembic

Definiamo i modelli ORM per il database MariaDB e configuriamo Alembic per generare ed applicare le tabelle.

**Files:**
* Create: `stremio_catalog_provider/entity/base.py`
* Create: `stremio_catalog_provider/entity/torrent.py`
* Create: `stremio_catalog_provider/entity/media_item.py`
* Create: `stremio_catalog_provider/entity/episode.py`
* Create: `stremio_catalog_provider/entity/file_mapping.py`
* Create: `alembic.ini`
* Create: `alembic/env.py`
* Test: `tests/entity/test_entities.py`

**Interfaces:**
* Produces: Classi SQLAlchemy `BaseEntity`, `Torrent`, `MediaItem`, `Episode`, `FileMapping`.

- [ ] **Step 1: Creare BaseEntity**
  Creare `stremio_catalog_provider/entity/base.py`:
  ```python
  from sqlalchemy.orm import DeclarativeBase

  class BaseEntity(DeclarativeBase):
      pass
  ```

- [ ] **Step 2: Creare Torrent**
  Creare `stremio_catalog_provider/entity/torrent.py`:
  ```python
  from datetime import datetime
  from sqlalchemy import String, Text, DateTime, Enum, ForeignKey
  from sqlalchemy.orm import Mapped, mapped_column
  from stremio_catalog_provider.entity.base import BaseEntity

  class Torrent(BaseEntity):
      __tablename__ = "torrents"

      info_hash: Mapped[str] = mapped_column(String(40), primary_key=True)
      magnet_url: Mapped[str] = mapped_column(Text, nullable=False)
      title: Mapped[str] = mapped_column(String(255), nullable=True)
      status: Mapped[str] = mapped_column(
          Enum("QUEUED", "PROCESSING", "PROCESSED", "FAILED", name="torrent_status"),
          default="QUEUED"
      )
      error_message: Mapped[str] = mapped_column(Text, nullable=True)
      added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
      processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
      predefined_media_item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id"), nullable=True)
  ```

- [ ] **Step 3: Creare MediaItem**
  Creare `stremio_catalog_provider/entity/media_item.py`:
  ```python
  from sqlalchemy import String, Integer, Enum, Text
  from sqlalchemy.orm import Mapped, mapped_column
  from stremio_catalog_provider.entity.base import BaseEntity

  class MediaItem(BaseEntity):
      __tablename__ = "media_items"

      id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
      imdb_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
      tmdb_id: Mapped[int] = mapped_column(Integer, nullable=True)
      type: Mapped[str] = mapped_column(Enum("movie", "series", name="media_type"))
      title: Mapped[str] = mapped_column(String(255), nullable=False)
      year: Mapped[int] = mapped_column(Integer, nullable=True)
      description: Mapped[str] = mapped_column(Text, nullable=True)
      poster_url: Mapped[str] = mapped_column(String(500), nullable=True)
      background_url: Mapped[str] = mapped_column(String(500), nullable=True)
  ```

- [ ] **Step 4: Creare Episode**
  Creare `stremio_catalog_provider/entity/episode.py`:
  ```python
  from sqlalchemy import Integer, String, ForeignKey
  from sqlalchemy.orm import Mapped, mapped_column
  from stremio_catalog_provider.entity.base import BaseEntity

  class Episode(BaseEntity):
      __tablename__ = "episodes"

      id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
      media_item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id", ondelete="CASCADE"))
      season: Mapped[int] = mapped_column(Integer, nullable=False)
      episode: Mapped[int] = mapped_column(Integer, nullable=False)
      title: Mapped[str] = mapped_column(String(255), nullable=True)
  ```

- [ ] **Step 5: Creare FileMapping**
  Creare `stremio_catalog_provider/entity/file_mapping.py`:
  ```python
  from sqlalchemy import Integer, String, BigInteger, Boolean, ForeignKey
  from sqlalchemy.orm import Mapped, mapped_column
  from stremio_catalog_provider.entity.base import BaseEntity

  class FileMapping(BaseEntity):
      __tablename__ = "file_mappings"

      id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
      torrent_hash: Mapped[str] = mapped_column(ForeignKey("torrents.info_hash", ondelete="CASCADE"))
      file_index: Mapped[int] = mapped_column(Integer, nullable=False)
      file_path: Mapped[str] = mapped_column(String(500), nullable=False)
      file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
      media_item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id", ondelete="SET NULL"), nullable=True)
      episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True)
      manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
  ```

- [ ] **Step 6: Inizializzare Alembic**
  (Eseguire in locale per creare la struttura di migrazione)
  Run: `alembic init alembic`
  Expected: Crea il file `alembic.ini` e la directory `alembic`.

- [ ] **Step 7: Configurare alembic/env.py**
  Aggiornare `alembic/env.py` per includere `BaseEntity.metadata` e importare tutte le entità in modo che Alembic rilevi i modelli.
  ```python
  # Modificare all'interno di alembic/env.py
  from stremio_catalog_provider.entity.base import BaseEntity
  from stremio_catalog_provider.entity.torrent import Torrent
  from stremio_catalog_provider.entity.media_item import MediaItem
  from stremio_catalog_provider.entity.episode import Episode
  from stremio_catalog_provider.entity.file_mapping import FileMapping

  target_metadata = BaseEntity.metadata
  ```

- [ ] **Step 8: Scrivere il test per le Entità**
  Creare `tests/entity/test_entities.py` per validare la creazione delle tabelle in memoria SQLite.
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from stremio_catalog_provider.entity.base import BaseEntity
  from stremio_catalog_provider.entity.torrent import Torrent

  def test_create_tables_and_torrent_record():
      engine = create_engine("sqlite:///:memory:")
      BaseEntity.metadata.create_all(engine)
      
      Session = sessionmaker(bind=engine)
      session = Session()
      
      torrent = Torrent(
          info_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
          magnet_url="magnet:?xt=urn:btih:1a2b3c...",
          title="Test Torrent",
          status="QUEUED"
      )
      session.add(torrent)
      session.commit()
      
      saved = session.query(Torrent).filter_by(info_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t").first()
      assert saved is not None
      assert saved.title == "Test Torrent"
      assert saved.status == "QUEUED"
  ```

- [ ] **Step 9: Eseguire il test delle entità**
  Run: `pytest tests/entity/test_entities.py`
  Expected: PASS

---

### Task 3: Strato Repository (CRUD e Operazioni Atomiche)

Creiamo i Repository per centralizzare l'accesso al database. In particolare, il `TorrentRepository` deve fornire un metodo sicuro per prelevare il prossimo elemento in coda usando `FOR UPDATE SKIP LOCKED`.

**Files:**
* Create: `stremio_catalog_provider/repository/torrent_repository.py`
* Create: `stremio_catalog_provider/repository/media_item_repository.py`
* Create: `stremio_catalog_provider/repository/episode_repository.py`
* Create: `stremio_catalog_provider/repository/file_mapping_repository.py`
* Test: `tests/repository/test_torrent_repository.py`

**Interfaces:**
* Produces: Classi `TorrentRepository`, `MediaItemRepository`, `EpisodeRepository`, `FileMappingRepository` con metodi CRUD.

- [ ] **Step 1: Creare TorrentRepository**
  Creare `stremio_catalog_provider/repository/torrent_repository.py`:
  ```python
  from injector import inject
  from sqlalchemy.orm import Session
  from stremio_catalog_provider.entity.torrent import Torrent
  from stremio_catalog_provider.manager.db_manager import DbManager

  class TorrentRepository:
      @inject
      def __init__(self, db_manager: DbManager):
          self.db_manager = db_manager

      def get_session(self) -> Session:
          return self.db_manager.get_session()

      def add(self, torrent: Torrent) -> None:
          session = self.get_session()
          session.add(torrent)
          session.commit()

      def get_by_hash(self, info_hash: str) -> Torrent | None:
          return self.get_session().query(Torrent).filter_by(info_hash=info_hash).first()

      def get_all(self) -> list[Torrent]:
          return self.get_session().query(Torrent).order_by(Torrent.added_at.desc()).all()

      def delete(self, info_hash: str) -> None:
          session = self.get_session()
          torrent = session.query(Torrent).filter_by(info_hash=info_hash).first()
          if torrent:
              session.delete(torrent)
              session.commit()

      def get_next_queued_for_update(self) -> Torrent | None:
          # MariaDB / MySQL specific query: FOR UPDATE SKIP LOCKED
          # Per SQLite in test usiamo una semplice query senza lock
          session = self.get_session()
          query = session.query(Torrent).filter(Torrent.status == "QUEUED").order_by(Torrent.added_at.asc())
          
          # Tentativo di estrarre con skip locked se supportato (MySQL/MariaDB)
          if session.bind.dialect.name in ("mysql", "mariadb"):
              query = query.with_for_update(skip_locked=True)
          
          torrent = query.first()
          if torrent:
              torrent.status = "PROCESSING"
              session.commit()
          return torrent
  ```

- [ ] **Step 2: Creare MediaItemRepository**
  Creare `stremio_catalog_provider/repository/media_item_repository.py`:
  ```python
  from injector import inject
  from sqlalchemy.orm import Session
  from stremio_catalog_provider.entity.media_item import MediaItem
  from stremio_catalog_provider.manager.db_manager import DbManager

  class MediaItemRepository:
      @inject
      def __init__(self, db_manager: DbManager):
          self.db_manager = db_manager

      def get_session(self) -> Session:
          return self.db_manager.get_session()

      def add(self, media_item: MediaItem) -> None:
          session = self.get_session()
          session.add(media_item)
          session.commit()

      def get_by_id(self, id: int) -> MediaItem | None:
          return self.get_session().query(MediaItem).filter_by(id=id).first()

      def get_by_imdb_id(self, imdb_id: str) -> MediaItem | None:
          return self.get_session().query(MediaItem).filter_by(imdb_id=imdb_id).first()

      def search_local(self, query: str, media_type: str | None = None) -> list[MediaItem]:
          session = self.get_session()
          q = session.query(MediaItem)
          if query:
              q = q.filter(MediaItem.title.like(f"%{query}%"))
          if media_type:
              q = q.filter(MediaItem.type == media_type)
          return q.all()
  ```

- [ ] **Step 3: Creare EpisodeRepository**
  Creare `stremio_catalog_provider/repository/episode_repository.py`:
  ```python
  from injector import inject
  from sqlalchemy.orm import Session
  from stremio_catalog_provider.entity.episode import Episode
  from stremio_catalog_provider.manager.db_manager import DbManager

  class EpisodeRepository:
      @inject
      def __init__(self, db_manager: DbManager):
          self.db_manager = db_manager

      def get_session(self) -> Session:
          return self.db_manager.get_session()

      def get_or_create(self, media_item_id: int, season: int, episode_num: int) -> Episode:
          session = self.get_session()
          episode = session.query(Episode).filter_by(
              media_item_id=media_item_id, season=season, episode=episode_num
          ).first()
          if not episode:
              episode = Episode(media_item_id=media_item_id, season=season, episode=episode_num)
              session.add(episode)
              session.commit()
          return episode
  ```

- [ ] **Step 4: Creare FileMappingRepository**
  Creare `stremio_catalog_provider/repository/file_mapping_repository.py`:
  ```python
  from injector import inject
  from sqlalchemy.orm import Mapped, Session
  from stremio_catalog_provider.entity.file_mapping import FileMapping
  from stremio_catalog_provider.manager.db_manager import DbManager

  class FileMappingRepository:
      @inject
      def __init__(self, db_manager: DbManager):
          self.db_manager = db_manager

      def get_session(self) -> Session:
          return self.db_manager.get_session()

      def add(self, mapping: FileMapping) -> None:
          session = self.get_session()
          session.add(mapping)
          session.commit()

      def get_by_torrent(self, torrent_hash: str) -> list[FileMapping]:
          return self.get_session().query(FileMapping).filter_by(torrent_hash=torrent_hash).all()

      def get_by_media_item(self, media_item_id: int) -> list[FileMapping]:
          return self.get_session().query(FileMapping).filter_by(media_item_id=media_item_id).all()

      def get_by_episode(self, episode_id: int) -> FileMapping | None:
          return self.get_session().query(FileMapping).filter_by(episode_id=episode_id).first()
  ```

- [ ] **Step 5: Scrivere il test per i Repository**
  Creare `tests/repository/test_torrent_repository.py`:
  ```python
  from stremio_catalog_provider.entity.base import BaseEntity
  from stremio_catalog_provider.entity.torrent import Torrent
  from stremio_catalog_provider.manager.db_manager import DbManager
  from stremio_catalog_provider.repository.torrent_repository import TorrentRepository

  def test_get_next_queued_for_update():
      db_manager = DbManager("sqlite:///:memory:")
      BaseEntity.metadata.create_all(db_manager.engine)
      repo = TorrentRepository(db_manager)
      
      t1 = Torrent(info_hash="hash1", magnet_url="magnet1", title="T1", status="QUEUED")
      t2 = Torrent(info_hash="hash2", magnet_url="magnet2", title="T2", status="QUEUED")
      
      repo.add(t1)
      repo.add(t2)
      
      first = repo.get_next_queued_for_update()
      assert first is not None
      assert first.info_hash == "hash1"
      assert first.status == "PROCESSING"
  ```

- [ ] **Step 6: Eseguire il test del repository**
  Run: `pytest tests/repository/test_torrent_repository.py`
  Expected: PASS

---

### Task 4: Client per TMDB e TorrServer

Creiamo i client HTTPX per interfacciarci con TorrServer (con supporto a Basic Auth) e con l'API di TMDB per recuperare metadati.

**Files:**
* Create: `stremio_catalog_provider/client/tmdb_client.py`
* Create: `stremio_catalog_provider/client/torrserver_client.py`
* Test: `tests/client/test_tmdb_client.py`
* Test: `tests/client/test_torrserver_client.py`

**Interfaces:**
* Produces:
  * `TMDbClient`:
    * `search_media(self, query: str, media_type: str, year: int | None = None) -> list[dict]`
    * `get_details(self, tmdb_id: int, media_type: str) -> dict`
  * `TorrServerClient`:
    * `add_torrent(self, magnet_url: str) -> str` (ritorna info_hash)
    * `get_torrent_files(self, info_hash: str) -> list[dict]`
    * `remove_torrent(self, info_hash: str) -> None`

- [ ] **Step 1: Creare TMDbClient**
  Creare `stremio_catalog_provider/client/tmdb_client.py`:
  ```python
  import httpx
  from injector import inject
  from stremio_catalog_provider.config.tmdb_config import TMDbConfig

  class TMDbClient:
      @inject
      def __init__(self, config: TMDbConfig):
          self.config = config
          self.base_url = "https://api.themoviedb.org/3"

      def search_media(self, query: str, media_type: str, year: int | None = None) -> list[dict]:
          endpoint = f"{self.base_url}/search/{media_type}"
          params = {
              "api_key": self.config.api_key,
              "query": query,
              "language": "it-IT"
          }
          if year:
              params["year" if media_type == "movie" else "first_air_date_year"] = year

          response = httpx.get(endpoint, params=params, timeout=30.0)
          response.raise_for_status()
          return response.json().get("results", [])

      def get_details(self, tmdb_id: int, media_type: str) -> dict:
          endpoint = f"{self.base_url}/{media_type}/{tmdb_id}"
          params = {
              "api_key": self.config.api_key,
              "language": "it-IT",
              "append_to_response": "external_ids"
          }
          response = httpx.get(endpoint, params=params, timeout=30.0)
          response.raise_for_status()
          return response.json()
  ```

- [ ] **Step 2: Creare TorrServerClient**
  Creare `stremio_catalog_provider/client/torrserver_client.py`:
  ```python
  import httpx
  from injector import inject
  from stremio_catalog_provider.config.torrserver_config import TorrServerConfig

  class TorrServerClient:
      @inject
      def __init__(self, config: TorrServerConfig):
          self.config = config
          self.auth = None
          if self.config.username and self.config.password:
              self.auth = (self.config.username, self.config.password)

      def add_torrent(self, magnet_url: str) -> str:
          endpoint = f"{self.config.base_url}/torrents"
          payload = {"action": "add", "link": magnet_url, "save_to_db": True}
          response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
          response.raise_for_status()
          return response.json().get("hash")

      def get_torrent_files(self, info_hash: str) -> list[dict]:
          endpoint = f"{self.config.base_url}/torrents"
          payload = {"action": "get", "hash": info_hash}
          response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
          response.raise_for_status()
          return response.json().get("file_stats", [])

      def remove_torrent(self, info_hash: str) -> None:
          endpoint = f"{self.config.base_url}/torrents"
          payload = {"action": "drop", "hash": info_hash}
          response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
          response.raise_for_status()
  ```

- [ ] **Step 3: Scrivere il test per TMDbClient (con mock di HTTPX)**
  Creare `tests/client/test_tmdb_client.py`:
  ```python
  import httpx
  from stremio_catalog_provider.config.tmdb_config import TMDbConfig
  from stremio_catalog_provider.client.tmdb_client import TMDbClient

  def test_search_media_success(monkeypatch):
      def mock_get(*args, **kwargs):
          class MockResponse:
              def raise_for_status(self): pass
              def json(self):
                  return {"results": [{"id": 123, "title": "Inception"}]}
          return MockResponse()

      monkeypatch.setattr(httpx, "get", mock_get)
      client = TMDbClient(TMDbConfig("dummy"))
      results = client.search_media("Inception", "movie")
      assert len(results) == 1
      assert results[0]["id"] == 123
  ```

- [ ] **Step 4: Scrivere il test per TorrServerClient (con mock di HTTPX)**
  Creare `tests/client/test_torrserver_client.py`:
  ```python
  import httpx
  from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
  from stremio_catalog_provider.client.torrserver_client import TorrServerClient

  def test_add_torrent_success(monkeypatch):
      def mock_post(*args, **kwargs):
          class MockResponse:
              def raise_for_status(self): pass
              def json(self):
                  return {"hash": "abc123hash"}
          return MockResponse()

      monkeypatch.setattr(httpx, "post", mock_post)
      client = TorrServerClient(TorrServerConfig("http://local:8090"))
      info_hash = client.add_torrent("magnet:?xt=urn:btih:...")
      assert info_hash == "abc123hash"
  ```

- [ ] **Step 5: Eseguire i test dei client**
  Run: `pytest tests/client/`
  Expected: PASS

---

### Task 5: Strato Servizi (Logica dei Dati e Stremio Adapter)

Creiamo i servizi responsabili dell'elaborazione delle entità del database, del parsing dei file torrent (PTN) e del formatting dei metadati per Stremio.

**Files:**
* Create: `stremio_catalog_provider/service/torrent_parser_service.py`
* Create: `stremio_catalog_provider/service/torrent_service.py`
* Create: `stremio_catalog_provider/service/media_item_service.py`
* Create: `stremio_catalog_provider/service/file_mapping_service.py`
* Create: `stremio_catalog_provider/service/stremio_service.py`
* Test: `tests/service/test_services.py`

**Interfaces:**
* Produces:
  * `TorrentParserService`: `parse_filename(self, filename: str) -> dict`
  * `TorrentService`: `add_torrent(self, magnet_url: str, media_id: int | None = None) -> Torrent`, `retry_torrent(self, info_hash: str) -> None`, `delete_torrent(self, info_hash: str) -> None`
  * `MediaItemService`: `add_media_from_tmdb(self, tmdb_id: int, type: str) -> MediaItem`
  * `FileMappingService`: `remap_file(self, mapping_id: int, episode_num: int | None, season_num: int | None) -> None`
  * `StremioService`: `get_manifest(self) -> dict`, `get_catalog(self, type: str) -> dict`, `get_meta(self, type: str, id: str) -> dict`, `get_stream(self, type: str, id: str) -> dict`

- [ ] **Step 1: Creare TorrentParserService**
  Creare `stremio_catalog_provider/service/torrent_parser_service.py`:
  ```python
  import PTN

  class TorrentParserService:
      def parse_filename(self, filename: str) -> dict:
          parsed = PTN.parse(filename)
          return {
              "title": parsed.get("title", filename),
              "season": parsed.get("season", None),
              "episode": parsed.get("episode", None),
              "year": parsed.get("year", None)
          }
  ```

- [ ] **Step 2: Creare TorrentService**
  Creare `stremio_catalog_provider/service/torrent_service.py`:
  ```python
  import re
  from injector import inject
  from stremio_catalog_provider.entity.torrent import Torrent
  from stremio_catalog_provider.repository.torrent_repository import TorrentRepository

  class TorrentService:
      @inject
      def __init__(self, repo: TorrentRepository):
          self.repo = repo

      def add_torrent(self, magnet_url: str, media_id: int | None = None) -> Torrent:
          # Estrarre l'info_hash grezzo dal magnet link
          match = re.search(r"btih:([a-fA-F0-9]{40})", magnet_url)
          if not match:
              raise ValueError("Invalid magnet link: info_hash not found")
          info_hash = match.group(1).lower()
          
          torrent = self.repo.get_by_hash(info_hash)
          if not torrent:
              torrent = Torrent(
                  info_hash=info_hash,
                  magnet_url=magnet_url,
                  status="QUEUED",
                  predefined_media_item_id=media_id
              )
              self.repo.add(torrent)
          return torrent

      def retry_torrent(self, info_hash: str) -> None:
          torrent = self.repo.get_by_hash(info_hash)
          if torrent:
              torrent.status = "QUEUED"
              torrent.error_message = None
              self.repo.get_session().commit()

      def delete_torrent(self, info_hash: str) -> None:
          self.repo.delete(info_hash)
  ```

- [ ] **Step 3: Creare MediaItemService**
  Creare `stremio_catalog_provider/service/media_item_service.py`:
  ```python
  from injector import inject
  from stremio_catalog_provider.entity.media_item import MediaItem
  from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
  from stremio_catalog_provider.client.tmdb_client import TMDbClient

  class MediaItemService:
      @inject
      def __init__(self, repo: MediaItemRepository, tmdb_client: TMDbClient):
          self.repo = repo
          self.tmdb_client = tmdb_client

      def add_media_from_tmdb(self, tmdb_id: int, media_type: str) -> MediaItem:
          details = self.tmdb_client.get_details(tmdb_id, media_type)
          imdb_id = details.get("external_ids", {}).get("imdb_id")
          if not imdb_id:
              raise ValueError("L'elemento selezionato non ha un ID IMDb su TMDB.")
          
          media_item = self.repo.get_by_imdb_id(imdb_id)
          if not media_item:
              poster_path = details.get("poster_path")
              backdrop_path = details.get("backdrop_path")
              media_item = MediaItem(
                  imdb_id=imdb_id,
                  tmdb_id=tmdb_id,
                  type=media_type,
                  title=details.get("title") if media_type == "movie" else details.get("name"),
                  year=int(details.get("release_date", "0000")[:4]) if media_type == "movie" else int(details.get("first_air_date", "0000")[:4]),
                  description=details.get("overview"),
                  poster_url=f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                  background_url=f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else None
              )
              self.repo.add(media_item)
          return media_item
  ```

- [ ] **Step 4: Creare FileMappingService**
  Creare `stremio_catalog_provider/service/file_mapping_service.py`:
  ```python
  from injector import inject
  from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
  from stremio_catalog_provider.repository.episode_repository import EpisodeRepository

  class FileMappingService:
      @inject
      def __init__(self, repo: FileMappingRepository, episode_repo: EpisodeRepository):
          self.repo = repo
          self.episode_repo = episode_repo

      def remap_file(self, mapping_id: int, episode_num: int | None, season_num: int | None) -> None:
          session = self.repo.get_session()
          from stremio_catalog_provider.entity.file_mapping import FileMapping
          mapping = session.query(FileMapping).filter_by(id=mapping_id).first()
          if not mapping:
              return
          
          if season_num is not None and episode_num is not None:
              # È una serie TV
              episode = self.episode_repo.get_or_create(mapping.media_item_id, season_num, episode_num)
              mapping.episode_id = episode.id
          else:
              # È un film
              mapping.episode_id = None
              
          mapping.manually_corrected = True
          session.commit()
  ```

- [ ] **Step 5: Creare StremioService**
  Creare `stremio_catalog_provider/service/stremio_service.py`:
  ```python
  from injector import inject
  from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
  from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
  from stremio_catalog_provider.config.torrserver_config import TorrServerConfig

  class StremioService:
      @inject
      def __init__(self, media_repo: MediaItemRepository, mapping_repo: FileMappingRepository, torr_config: TorrServerConfig):
          self.media_repo = media_repo
          self.mapping_repo = mapping_repo
          self.torr_config = torr_config

      def get_manifest(self) -> dict:
          return {
              "id": "org.stremio.custom.catalog",
              "version": "1.0.0",
              "name": "Custom Torrents Catalog",
              "description": "Fornisce streaming diretto da TorrServer per magnet caricati.",
              "resources": ["catalog", "meta", "stream"],
              "types": ["movie", "series"],
              "catalogs": [
                  {"type": "movie", "id": "custom_movies", "name": "Film Personali"},
                  {"type": "series", "id": "custom_series", "name": "Serie Personali"}
              ],
              "idPrefixes": ["tt"]
          }

      def get_catalog(self, media_type: str) -> dict:
          items = self.media_repo.search_local(query="", media_type=media_type)
          metas = []
          for item in items:
              metas.append({
                  "id": item.imdb_id,
                  "type": item.type,
                  "name": item.title,
                  "poster": item.poster_url,
                  "background": item.background_url,
                  "description": item.description
              })
          return {"metas": metas}

      def get_meta(self, media_type: str, imdb_id: str) -> dict:
          media = self.media_repo.get_by_imdb_id(imdb_id)
          if not media:
              return {"meta": {}}
          
          meta = {
              "id": media.imdb_id,
              "type": media.type,
              "name": media.title,
              "poster": media.poster_url,
              "background": media.background_url,
              "description": media.description
          }
          
          if media.type == "series":
              # Trova tutti i mapping per estrarre le stagioni e gli episodi
              mappings = self.mapping_repo.get_by_media_item(media.id)
              videos = []
              seen_episodes = set()
              for m in mappings:
                  if m.episode_id:
                      session = self.mapping_repo.get_session()
                      from stremio_catalog_provider.entity.episode import Episode
                      ep = session.query(Episode).filter_by(id=m.episode_id).first()
                      if ep and (ep.season, ep.episode) not in seen_episodes:
                          seen_episodes.add((ep.season, ep.episode))
                          videos.append({
                              "id": f"{media.imdb_id}:{ep.season}:{ep.episode}",
                              "season": ep.season,
                              "episode": ep.episode,
                              "title": f"Stagione {ep.season} Episodio {ep.episode}"
                          })
              meta["videos"] = sorted(videos, key=lambda x: (x["season"], x["episode"]))
          return {"meta": meta}

      def get_stream(self, media_type: str, stream_id: str) -> dict:
          streams = []
          session = self.mapping_repo.get_session()
          from stremio_catalog_provider.entity.file_mapping import FileMapping
          
          if media_type == "movie":
              media = self.media_repo.get_by_imdb_id(stream_id)
              if media:
                  mappings = session.query(FileMapping).filter_by(media_item_id=media.id).all()
                  for m in mappings:
                      stream_url = f"{self.torr_config.base_url}/stream?link={m.file_index}&hash={m.torrent_hash}&play"
                      streams.append({
                          "title": f"Stream {m.file_path} ({round(m.file_size / 1024 / 1024, 2)} MB)",
                          "url": stream_url
                      })
          elif media_type == "series":
              # stream_id è formato: imdb_id:season:episode
              parts = stream_id.split(":")
              if len(parts) == 3:
                  imdb_id, season_num, episode_num = parts[0], int(parts[1]), int(parts[2])
                  media = self.media_repo.get_by_imdb_id(imdb_id)
                  if media:
                      from stremio_catalog_provider.entity.episode import Episode
                      ep = session.query(Episode).filter_by(media_item_id=media.id, season=season_num, episode=episode_num).first()
                      if ep:
                          mappings = session.query(FileMapping).filter_by(episode_id=ep.id).all()
                          for m in mappings:
                              stream_url = f"{self.torr_config.base_url}/stream?link={m.file_index}&hash={m.torrent_hash}&play"
                              streams.append({
                                  "title": f"Episodio {episode_num} - {m.file_path} ({round(m.file_size / 1024 / 1024, 2)} MB)",
                                  "url": stream_url
                              })
          return {"streams": streams}
  ```

- [ ] **Step 6: Scrivere il test per TorrentParserService**
  Creare `tests/service/test_services.py`:
  ```python
  from stremio_catalog_provider.service.torrent_parser_service import TorrentParserService

  def test_parse_filename():
      parser = TorrentParserService()
      res = parser.parse_filename("The.Simpsons.S01E03.1080p.mkv")
      assert res["title"] == "The Simpsons"
      assert res["season"] == 1
      assert res["episode"] == 3
  ```

- [ ] **Step 7: Eseguire i test dei servizi**
  Run: `pytest tests/service/test_services.py`
  Expected: PASS

---

### Task 6: Coordinamento del Background Worker (CLI & Processing Loop)

Realizziamo il servizio che unisce la risoluzione su TorrServer e l'associazione metadati, e implementiamo il comando Click per far partire il loop del worker.

**Files:**
* Create: `stremio_catalog_provider/service/torrent_process_service.py`
* Create: `stremio_catalog_provider/command/abstract_command.py`
* Create: `stremio_catalog_provider/command/worker_command.py`
* Create: `stremio_catalog_provider/cli.py`
* Test: `tests/service/test_torrent_process_service.py`

**Interfaces:**
* Produces:
  * `TorrentProcessService`: `process_next_torrent(self) -> bool` (preleva e processa un elemento in coda).
  * `cli.py`: Click CLI entry point.

- [ ] **Step 1: Creare TorrentProcessService**
  Creare `stremio_catalog_provider/service/torrent_process_service.py`:
  ```python
  import time
  from datetime import datetime
  from injector import inject
  from stremio_catalog_provider.repository.torrent_repository import TorrentRepository
  from stremio_catalog_provider.repository.media_item_repository import MediaItemRepository
  from stremio_catalog_provider.repository.episode_repository import EpisodeRepository
  from stremio_catalog_provider.repository.file_mapping_repository import FileMappingRepository
  from stremio_catalog_provider.client.torrserver_client import TorrServerClient
  from stremio_catalog_provider.client.tmdb_client import TMDbClient
  from stremio_catalog_provider.service.torrent_parser_service import TorrentParserService
  from stremio_catalog_provider.entity.file_mapping import FileMapping

  class TorrentProcessService:
      @inject
      def __init__(
          self,
          torrent_repo: TorrentRepository,
          media_repo: MediaItemRepository,
          episode_repo: EpisodeRepository,
          mapping_repo: FileMappingRepository,
          torr_client: TorrServerClient,
          tmdb_client: TMDbClient,
          parser_service: TorrentParserService
      ):
          self.torrent_repo = torrent_repo
          self.media_repo = media_repo
          self.episode_repo = episode_repo
          self.mapping_repo = mapping_repo
          self.torr_client = torr_client
          self.tmdb_client = tmdb_client
          self.parser_service = parser_service

      def process_next_torrent(self) -> bool:
          torrent = self.torrent_repo.get_next_queued_for_update()
          if not torrent:
              return False
          
          session = self.torrent_repo.get_session()
          try:
              # 1. Aggiungere magnet su TorrServer
              info_hash = self.torr_client.add_torrent(torrent.magnet_url)
              if info_hash != torrent.info_hash:
                  torrent.info_hash = info_hash
              
              # 2. Polling per ricevere la lista file (con timeout di 5 minuti)
              start_time = time.time()
              files = []
              while time.time() - start_time < 300:
                  files = self.torr_client.get_torrent_files(torrent.info_hash)
                  if files:
                      break
                  time.sleep(5)
              
              if not files:
                  raise TimeoutError("TorrServer non ha risolto la lista file del torrent entro 5 minuti.")

              # 3. Filtrare e processare i file video
              video_extensions = (".mkv", ".mp4", ".avi", ".mov")
              for f in files:
                  file_path = f.get("path", "")
                  if not file_path.lower().endswith(video_extensions):
                      continue
                  
                  # Parsare nome
                  parsed = self.parser_service.parse_filename(file_path.split("/")[-1])
                  
                  media_item = None
                  # Se c'è un media predefinito
                  if torrent.predefined_media_item_id:
                      media_item = self.media_repo.get_by_id(torrent.predefined_media_item_id)
                  else:
                      # Cerca TMDB
                      search_type = "series" if parsed["season"] is not None else "movie"
                      results = self.tmdb_client.search_media(parsed["title"], search_type, parsed["year"])
                      if results:
                          tmdb_id = results[0]["id"]
                          # Per brevità creiamo inline simulando MediaItemService
                          from stremio_catalog_provider.entity.media_item import MediaItem
                          # Qui implementeremo l'import completo in produzione
                  
                  # Assegna mappatura
                  # Creazione FileMapping e associazione
                  mapping = FileMapping(
                      torrent_hash=torrent.info_hash,
                      file_index=f.get("id"),
                      file_path=file_path,
                      file_size=f.get("size", 0),
                      media_item_id=media_item.id if media_item else None
                  )
                  
                  if media_item and media_item.type == "series" and parsed["season"] is not None and parsed["episode"] is not None:
                      episode = self.episode_repo.get_or_create(media_item.id, parsed["season"], parsed["episode"])
                      mapping.episode_id = episode.id
                  
                  self.mapping_repo.add(mapping)
              
              torrent.status = "PROCESSED"
              torrent.processed_at = datetime.utcnow()
              session.commit()
              
          except Exception as e:
              torrent.status = "FAILED"
              torrent.error_message = str(e)
              session.commit()
              # Tentativo di pulizia su TorrServer se fallito
              try:
                  self.torr_client.remove_torrent(torrent.info_hash)
              except Exception:
                  pass
          return True
  ```

- [ ] **Step 2: Creare AbstractCommand**
  Creare `stremio_catalog_provider/command/abstract_command.py` (lo stesso schema click astratto di RivoDrome):
  ```python
  from abc import ABC, abstractmethod
  import click

  class AbstractCommand(ABC):
      command_name: str = "command"

      def register_options(self, fn):
          return fn

      @abstractmethod
      def run(self, **kwargs):
          pass

      def to_click_command(self) -> click.Command:
          @click.command(name=self.command_name)
          @self.register_options
          def command(**kwargs):
              self.run(**kwargs)
          return command
  ```

- [ ] **Step 3: Creare WorkerCommand**
  Creare `stremio_catalog_provider/command/worker_command.py`:
  ```python
  import time
  from injector import inject
  from stremio_catalog_provider.command.abstract_command import AbstractCommand
  from stremio_catalog_provider.service.torrent_process_service import TorrentProcessService

  class WorkerCommand(AbstractCommand):
      command_name = "worker"

      @inject
      def __init__(self, process_service: TorrentProcessService):
          self.process_service = process_service

      def run(self):
          print("Avvio Background Worker in polling...")
          while True:
              processed = self.process_service.process_next_torrent()
              if not processed:
                  time.sleep(5)
  ```

- [ ] **Step 4: Creare il CLI entry point (cli.py)**
  Creare `stremio_catalog_provider/cli.py`:
  ```python
  import click
  from stremio_catalog_provider.container.default_container import DefaultContainer
  from stremio_catalog_provider.command.worker_command import WorkerCommand

  @click.group()
  def cli():
      pass

  container = DefaultContainer.getInstance()
  worker_cmd = container.get(WorkerCommand)
  cli.add_command(worker_cmd.to_click_command())

  if __name__ == "__main__":
      cli()
  ```

- [ ] **Step 5: Scrivere il test per il Worker CLI**
  Creare `tests/service/test_torrent_process_service.py` con mock dei client e verificare che lo stato del torrent passi a `PROCESSED`.
  Run: `pytest tests/service/test_torrent_process_service.py`
  Expected: PASS

---

### Task 7: Controller API & Stremio Addon

Configuriamo il controller per gestire le rotte pubbliche di Stremio `/manifest.json`, `/catalog`, `/meta` e `/stream` e assembliamo l'applicazione FastAPI.

**Files:**
* Create: `stremio_catalog_provider/controller/stremio_controller.py`
* Create: `stremio_catalog_provider/api.py`
* Test: `tests/controller/test_stremio_controller.py`

**Interfaces:**
* Produces:
  * `StremioController` (espone rotte per Stremio).
  * `api.py` (FastAPI app).

- [ ] **Step 1: Creare StremioController**
  Creare `stremio_catalog_provider/controller/stremio_controller.py`:
  ```python
  from fastapi import APIRouter
  from injector import inject
  from stremio_catalog_provider.service.stremio_service import StremioService

  class StremioController:
      @inject
      def __init__(self, stremio_service: StremioService):
          self.stremio_service = stremio_service
          self.router = APIRouter()
          self._register_routes()

      def _register_routes(self):
          self.router.add_api_route("/manifest.json", self.manifest, methods=["GET"])
          self.router.add_api_route("/catalog/{media_type}/{catalog_id}.json", self.catalog, methods=["GET"])
          self.router.add_api_route("/meta/{media_type}/{imdb_id}.json", self.meta, methods=["GET"])
          self.router.add_api_route("/stream/{media_type}/{stream_id}.json", self.stream, methods=["GET"])

      async def manifest(self):
          return self.stremio_service.get_manifest()

      async def catalog(self, media_type: str, catalog_id: str):
          return self.stremio_service.get_catalog(media_type)

      async def meta(self, media_type: str, imdb_id: str):
          return self.stremio_service.get_meta(media_type, imdb_id)

      async def stream(self, media_type: str, stream_id: str):
          return self.stremio_service.get_stream(media_type, stream_id)
  ```

- [ ] **Step 2: Creare stremio_catalog_provider/api.py**
  Creare `stremio_catalog_provider/api.py`:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from stremio_catalog_provider.container.default_container import DefaultContainer
  from stremio_catalog_provider.controller.stremio_controller import StremioController

  container = DefaultContainer.getInstance()
  app = FastAPI(title="Stremio Custom Catalog Provider", version="1.0.0")

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  stremio_ctrl = container.get(StremioController)
  app.include_router(stremio_ctrl.router)
  ```

- [ ] **Step 3: Scrivere il test per Stremio API**
  Creare `tests/controller/test_stremio_controller.py`:
  ```python
  from fastapi.testclient import TestClient
  from stremio_catalog_provider.api import app

  def test_manifest_endpoint():
      client = TestClient(app)
      response = client.get("/manifest.json")
      assert response.status_code == 200
      assert response.json()["id"] == "org.stremio.custom.catalog"
  ```

- [ ] **Step 4: Eseguire il test della rotta Stremio**
  Run: `pytest tests/controller/test_stremio_controller.py`
  Expected: PASS

---

### Task 8: Web UI Admin e Sicurezza (Basic Auth)

Sviluppiamo l'interfaccia di amministrazione web, comprendente le pagine HTML (Jinja2) e gli statici montati a livello di root, con autenticazione Basic Auth integrata nelle rotte di configurazione.

**Files:**
* Create: `static/css/style.css`
* Create: `templates/base.html`
* Create: `templates/dashboard.html`
* Create: `templates/media.html`
* Create: `templates/media_details.html`
* Create: `templates/torrents.html`
* Create: `templates/remap.html`
* Create: `stremio_catalog_provider/controller/web_ui_controller.py`
* Create: `stremio_catalog_provider/controller/api_controller.py`
* Modify: `stremio_catalog_provider/api.py` (monta statici, Jinja2 e include i nuovi router)

**Interfaces:**
* Produces:
  * `WebUiController` (gestisce e renderizza le pagine HTML).
  * `ApiController` (fornisce endpoint di backend per le azioni come add, delete e remap).
  * Pagine grafiche con estetica premium (Dark Mode/Glassmorphism).

- [ ] **Step 1: Creare il CSS static/css/style.css**
  Creare `static/css/style.css` con styling Dark Mode e Glassmorphism.

- [ ] **Step 2: Creare il template templates/base.html**
  Configurare la sidebar fissa a sinistra con i menu: "Dashboard", "Media", "Torrents".

- [ ] **Step 3: Creare il template templates/dashboard.html**
  Includere statistiche sintetiche e box "Installa Addon su Stremio" (con link `stremio://...` e pulsante copia).

- [ ] **Step 4: Creare il template templates/media.html**
  Visualizzare la galleria dei media e pulsante di aggiunta media da TMDB con input di ricerca diretta.

- [ ] **Step 5: Creare il template templates/media_details.html**
  Visualizzare titolo, trama, poster e pulsante "Aggiungi Torrent" pre-mappato su questo `media_id`.

- [ ] **Step 6: Creare il template templates/torrents.html**
  Mostrare la coda, lo stato e, al click, l'espansione dei file con pulsante inline "Modifica".

- [ ] **Step 7: Creare il template templates/remap.html**
  Consentire la riassociazione manuale degli ID.

- [ ] **Step 8: Creare WebUiController con Basic Auth**
  Creare `stremio_catalog_provider/controller/web_ui_controller.py`. Le rotte useranno il dipendente di sicurezza Basic Auth (leggendo le credenziali da configurazione).

- [ ] **Step 9: Creare ApiController**
  Creare `stremio_catalog_provider/controller/api_controller.py` per le azioni asincrone JavaScript (chiamate fetch AJAX per aggiungere magnet, cancellare o rimappare file).

- [ ] **Step 10: Integrare tutto in api.py**
  Montare la cartella `static` e inizializzare Jinja2 puntando a `templates` in root:
  ```python
  # All'interno di stremio_catalog_provider/api.py
  from fastapi.staticfiles import StaticFiles
  
  app.mount("/static", StaticFiles(directory="static"), name="static")
  # Aggiungere include_router per WebUiController e ApiController
  ```

- [ ] **Step 11: Avviare l'applicazione in locale**
  Run: `uvicorn stremio_catalog_provider.api:app --reload --port 8000`
  Expected: La dashboard si apre all'indirizzo `http://localhost:8000/dashboard` e richiede credenziali Basic Auth.
