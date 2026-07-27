# DB Refactoring and UI Extensions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactoring del database per introdurre l'ID incrementale su Torrent, recupero automatico del titolo da TorrServer con fallback PTN, nuova pagina di inserimento media separata `/media/add` e pagina di modifica torrent con re-mapping automatico.

**Architecture:** Modifica dei modelli SQLAlchemy e dei file di migrazione esistenti. Modifiche ai client e servizi per gestire le nuove join ed associazioni. Creazione di controller e rotte Web UI per le nuove pagine con relativi template Jinja2.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, Alembic, MariaDB, HTTPX, PTN, Injector, Click, Pytest, Jinja2, Vanilla CSS.

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

### Task 1: Refactoring dei Modelli Database ed Allineamento Migrazioni Alembic

**Files:**
* Modify: `stremio_catalog_provider/entity/torrent.py`
* Modify: `stremio_catalog_provider/entity/file_mapping.py`
* Modify: `alembic/versions/1002_create_torrents.py`
* Modify: `alembic/versions/1004_create_file_mappings.py`
* Modify: `tests/entity/test_entities.py`

**Interfaces:**
* Produces: `Torrent.id` (Primary Key incrementale), `Torrent.info_hash` (Unique Index), `FileMapping.torrent_id` (ForeignKey) e la property `@property def torrent_hash` su `FileMapping`.

- [ ] **Step 1: Scrivere il test fallimentare per i nuovi modelli**
  Aggiungere un test in `tests/entity/test_entities.py` che verifichi l'uso di `id` incrementale per `Torrent` e il collegamento `torrent_id` per `FileMapping`:
  ```python
  def test_torrent_id_relationship() -> None:
      engine = create_engine("sqlite:///:memory:")
      BaseEntity.metadata.create_all(engine)
      Session = sessionmaker(bind=engine)
      session = Session()

      # Creazione Torrent
      torrent = Torrent(
          info_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
          magnet_url="magnet:?xt=urn:btih:1a2b3c...",
          title="Test Torrent"
      )
      session.add(torrent)
      session.commit()

      assert torrent.id is not None  # Deve avere un ID numerico autoincrementale

      # Creazione FileMapping associato
      mapping = FileMapping(
          torrent_id=torrent.id,
          file_index=0,
          file_path="video.mkv",
          file_size=1000000,
          manually_corrected=False
      )
      session.add(mapping)
      session.commit()

      assert mapping.torrent_hash == "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t"
  ```

- [ ] **Step 2: Eseguire il test per verificarne il fallimento**
  Eseguire: `python -m pytest tests/entity/test_entities.py -k test_torrent_id_relationship`
  Expected: Fallisce con errori di compilazione/importazione dovuti a proprietà mancanti (`torrent_id`, `torrent` relationship).

- [ ] **Step 3: Modificare il modello Torrent**
  Aggiornare `stremio_catalog_provider/entity/torrent.py`:
  ```python
  from datetime import datetime
  from typing import Optional, List
  from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from stremio_catalog_provider.entity.base import BaseEntity

  class Torrent(BaseEntity):
      """SQLAlchemy model representing a Torrent."""

      __tablename__ = "torrents"

      id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
      info_hash: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
      magnet_url: Mapped[str] = mapped_column(Text, nullable=False)
      title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
      status: Mapped[str] = mapped_column(
          Enum("QUEUED", "PROCESSING", "PROCESSED", "FAILED", name="torrent_status"),
          default="QUEUED",
          index=True
      )
      error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
      added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
      processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
      predefined_media_item_id: Mapped[Optional[int]] = mapped_column(
          ForeignKey("media_items.id"), nullable=True
      )

      # Relationship back-reference
      mappings: Mapped[List["FileMapping"]] = relationship("FileMapping", back_populates="torrent", cascade="all, delete-orphan")
  ```

- [ ] **Step 4: Modificare il modello FileMapping**
  Aggiornare `stremio_catalog_provider/entity/file_mapping.py`:
  ```python
  from typing import Optional
  from sqlalchemy import Integer, String, BigInteger, Boolean, ForeignKey
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from stremio_catalog_provider.entity.base import BaseEntity

  class FileMapping(BaseEntity):
      """SQLAlchemy model representing a mapping between a torrent file and a MediaItem/Episode."""

      __tablename__ = "file_mappings"

      id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
      torrent_id: Mapped[int] = mapped_column(
          ForeignKey("torrents.id", ondelete="CASCADE"), nullable=False
      )
      file_index: Mapped[int] = mapped_column(Integer, nullable=False)
      file_path: Mapped[str] = mapped_column(String(500), nullable=False)
      file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
      media_item_id: Mapped[Optional[int]] = mapped_column(
          ForeignKey("media_items.id", ondelete="SET NULL"), nullable=True
      )
      episode_id: Mapped[Optional[int]] = mapped_column(
          ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True
      )
      manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

      # Relazioni
      torrent: Mapped["Torrent"] = relationship("Torrent", back_populates="mappings")

      @property
      def torrent_hash(self) -> str:
          return self.torrent.info_hash
  ```

- [ ] **Step 5: Verificare il superamento del test**
  Eseguire: `python -m pytest tests/entity/test_entities.py`
  Expected: Tutti i test in `test_entities.py` (incluso quello nuovo) passano con successo.

- [ ] **Step 6: Modificare la migrazione di Alembic per Torrent**
  Aggiornare `alembic/versions/1002_create_torrents.py` sostituendo la funzione `upgrade` e `downgrade`:
  ```python
  def upgrade() -> None:
      op.create_table(
          'torrents',
          sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
          sa.Column('info_hash', sa.String(length=40), nullable=False),
          sa.Column('magnet_url', sa.Text(), nullable=False),
          sa.Column('title', sa.String(length=255), nullable=True),
          sa.Column('status', sa.Enum('QUEUED', 'PROCESSING', 'PROCESSED', 'FAILED', name='torrent_status'), nullable=False),
          sa.Column('error_message', sa.Text(), nullable=True),
          sa.Column('added_at', sa.DateTime(), nullable=False),
          sa.Column('processed_at', sa.DateTime(), nullable=True),
          sa.Column('predefined_media_item_id', sa.Integer(), nullable=True),
          sa.ForeignKeyConstraint(['predefined_media_item_id'], ['media_items.id'], ),
          sa.PrimaryKeyConstraint('id'),
          sa.UniqueConstraint('info_hash')
      )
      op.create_index('ix_torrents_status', 'torrents', ['status'], unique=False)
  ```

- [ ] **Step 7: Modificare la migrazione di Alembic per FileMapping**
  Aggiornare `alembic/versions/1004_create_file_mappings.py`:
  ```python
  def upgrade() -> None:
      op.create_table(
          'file_mappings',
          sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
          sa.Column('torrent_id', sa.Integer(), nullable=False),
          sa.Column('file_index', sa.Integer(), nullable=False),
          sa.Column('file_path', sa.String(length=500), nullable=False),
          sa.Column('file_size', sa.BigInteger(), nullable=False),
          sa.Column('media_item_id', sa.Integer(), nullable=True),
          sa.Column('episode_id', sa.Integer(), nullable=True),
          sa.Column('manually_corrected', sa.Boolean(), nullable=False),
          sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='SET NULL'),
          sa.ForeignKeyConstraint(['media_item_id'], ['media_items.id'], ondelete='SET NULL'),
          sa.ForeignKeyConstraint(['torrent_id'], ['torrents.id'], ondelete='CASCADE'),
          sa.PrimaryKeyConstraint('id')
      )
  ```

---

### Task 2: Aggiornamento dei Repository, Servizi e Controller

Dobbiamo allineare tutte le query, le operazioni CRUD e i test che utilizzavano `torrent_hash` (nella tabella `file_mappings`) per fare riferimento a `torrent_id` o per caricare il Torrent.

**Files:**
* Modify: `stremio_catalog_provider/repository/torrent_repository.py`
* Modify: `stremio_catalog_provider/repository/file_mapping_repository.py`
* Modify: `stremio_catalog_provider/service/torrent_service.py`
* Modify: `stremio_catalog_provider/service/torrent_process_service.py`
* Modify: `stremio_catalog_provider/controller/web_ui_controller.py`
* Modify: `stremio_catalog_provider/controller/api_controller.py`
* Modify: `tests/repository/test_torrent_repository.py`
* Modify: `tests/service/test_services.py`
* Modify: `tests/service/test_torrent_process_service.py`
* Modify: `tests/controller/test_stremio_controller.py`
* Modify: `tests/controller/test_web_ui_auth.py`

**Interfaces:**
* Consumes: Modelli di database aggiornati nel Task 1.
* Produces:
  * `TorrentRepository.get_by_id(torrent_id: int) -> Torrent | None`
  * `FileMappingRepository.get_by_torrent(torrent_id: int) -> list[FileMapping]`

- [ ] **Step 1: Aggiungere il test per TorrentRepository.get_by_id**
  Aprire `tests/repository/test_torrent_repository.py` e aggiungere la verifica di `get_by_id`:
  ```python
  def test_get_by_id() -> None:
      db_manager = DbManager("sqlite:///:memory:")
      BaseEntity.metadata.create_all(db_manager.engine)
      repo = TorrentRepository(db_manager)

      t = Torrent(info_hash="hash1", magnet_url="magnet1", title="T1", status="QUEUED")
      repo.add(t)
      
      assert t.id is not None
      fetched = repo.get_by_id(t.id)
      assert fetched is not None
      assert fetched.info_hash == "hash1"
  ```
  Modificare anche `test_get_next_queued_for_update` per rispecchiare che i torrent vengono inseriti correttamente.

- [ ] **Step 2: Modificare TorrentRepository**
  In `stremio_catalog_provider/repository/torrent_repository.py`:
  * Aggiungere `get_by_id`:
    ```python
    def get_by_id(self, torrent_id: int) -> Torrent | None:
        return self.get_session().query(Torrent).filter_by(id=torrent_id).first()
    ```

- [ ] **Step 3: Modificare FileMappingRepository**
  In `stremio_catalog_provider/repository/file_mapping_repository.py` cambiare il metodo `get_by_torrent`:
  ```python
      def get_by_torrent(self, torrent_id: int) -> list[FileMapping]:
          return self.get_session().query(FileMapping).filter_by(torrent_id=torrent_id).all()
  ```

- [ ] **Step 4: Aggiornare TorrentProcessService**
  In `stremio_catalog_provider/service/torrent_process_service.py` cambiare l'istanziazione di `FileMapping` (linee 103-109):
  ```python
                  mapping = FileMapping(
                      torrent_id=torrent.id,
                      file_index=f.get("id"),
                      file_path=file_path,
                      file_size=f.get("size", 0),
                      media_item_id=media_item.id if media_item else None
                  )
  ```

- [ ] **Step 5: Aggiornare Web UI Controller e API Controller**
  * In `stremio_catalog_provider/controller/web_ui_controller.py`:
    * Nella rotta `remap` (linea 164), caricare il torrent partendo dal mapping:
      `torrent = mapping.torrent`
    * Nella rotta `media_details` (linee 122-127), caricare i torrent tramite join o relazione:
      ```python
      all_mappings = self.mapping_repo.get_by_media_item(media_id)
      torrents = {m.torrent for m in all_mappings if m.torrent is not None}
      torrents = sorted(list(torrents), key=lambda x: x.added_at, reverse=True)
      ```
  * In `stremio_catalog_provider/controller/api_controller.py`:
    * Nella rotta `get_mappings` (linee 120-121): caricare il torrent per hash e poi i suoi mapping:
      ```python
      torrent = self.torrent_repo.get_by_hash(info_hash)
      if not torrent:
          return {"mappings": []}
      mappings = self.mapping_repo.get_by_torrent(torrent.id)
      ```

- [ ] **Step 6: Sistemare e aggiornare i file di test rimanenti**
  * In `tests/service/test_services.py`, `tests/service/test_torrent_process_service.py`, `tests/controller/test_stremio_controller.py`:
    * Trovare le istanziazioni di `FileMapping` e sostituire il parametro `torrent_hash="..."` con `torrent_id=...` (oppure creare un `Torrent` fittizio nel DB di test e passarne l'ID).
  * Eseguire tutti i test per verificare la correttezza: `python -m pytest`
  * Risolvere eventuali errori o disallineamenti di tipo.

---

### Task 3: Risoluzione Automatica dei Titoli da TorrServer con Fallback PTN

**Files:**
* Modify: `stremio_catalog_provider/client/torrserver_client.py`
* Modify: `stremio_catalog_provider/service/torrent_process_service.py`
* Modify: `tests/client/test_torrserver_client.py`
* Modify: `tests/service/test_torrent_process_service.py`

**Interfaces:**
* Consumes: `TorrentParserService.parse_filename`
* Produces: `TorrServerClient.get_torrent(info_hash: str) -> dict[str, Any]`

- [ ] **Step 1: Aggiungere test per TorrServerClient.get_torrent**
  In `tests/client/test_torrserver_client.py`, aggiungere la verifica del nuovo metodo:
  ```python
  def test_get_torrent(httpx_mock) -> None:
      config = TorrServerConfig(base_url="http://localhost:8090")
      client = TorrServerClient(config)
      
      httpx_mock.add_response(
          method="POST",
          url="http://localhost:8090/torrents",
          json={"hash": "hash123", "title": "My Super Torrent", "file_stats": []}
      )
      
      data = client.get_torrent("hash123")
      assert data["title"] == "My Super Torrent"
  ```

- [ ] **Step 2: Implementare get_torrent nel client**
  In `stremio_catalog_provider/client/torrserver_client.py`:
  ```python
      def get_torrent(self, info_hash: str) -> dict[str, Any]:
          """Retrieves the full torrent details from TorrServer."""
          endpoint = f"{self.config.base_url}/torrents"
          payload = {"action": "get", "hash": info_hash}
          response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
          response.raise_for_status()
          return response.json()
  ```

- [ ] **Step 3: Aggiungere test di fallback PTN in TorrentProcessService**
  In `tests/service/test_torrent_process_service.py`, aggiungere un test per verificare che il titolo venga impostato con PTN se non fornito da TorrServer:
  ```python
  def test_process_next_torrent_fallback_title_ptn(monkeypatch, session) -> None:
      # Setup fittizio del client TorrServer
      # Verificare che se get_torrent non ritorna title, si usa il primo file video (es. "The.Matrix.1999.mkv")
      # e il torrent riceve come title "The Matrix"
      pass # L'implementazione completa del test sarà scritta inline
  ```

- [ ] **Step 4: Aggiornare TorrentProcessService per popolare il titolo**
  In `stremio_catalog_provider/service/torrent_process_service.py`, modificare la logica di polling nel metodo `process_next_torrent`:
  ```python
              # 2. Polling for file list resolution
              start_time = time.time()
              files = []
              while time.time() - start_time < poll_timeout:
                  torrent_data = self.torr_client.get_torrent(torrent.info_hash)
                  files = torrent_data.get("file_stats", [])
                  title = torrent_data.get("title")

                  # Fallback PTN: Se il titolo del torrent non è risolto da TorrServer, usa il primo file video
                  if not title and files:
                      video_extensions = (".mkv", ".mp4", ".avi", ".mov")
                      first_video = next(
                          (f.get("path", "").split("/")[-1] for f in files if f.get("path", "").lower().endswith(video_extensions)),
                          None
                      )
                      if first_video:
                          parsed_file = self.parser_service.parse_filename(first_video)
                          title = parsed_file.get("title")

                  if title and title != torrent.title:
                      torrent.title = title
                      session.commit()

                  if files:
                      break
                  time.sleep(poll_interval)
  ```

- [ ] **Step 5: Eseguire i test di client e worker**
  Eseguire: `python -m pytest tests/client/test_torrserver_client.py tests/service/test_torrent_process_service.py`
  Expected: Pass.

---

### Task 4: UI/Web - Pagina Separata di Aggiunta Media (`/media/add`)

**Files:**
* Modify: `stremio_catalog_provider/controller/web_ui_controller.py`
* Modify: `templates/media.html`
* Create: `templates/media_add.html`

**Interfaces:**
* Consumes: Rotte esistenti `/api/tmdb/search` e `/api/media`.
* Produces: Rotta Web `GET /media/add`.

- [ ] **Step 1: Aggiungere rotta media_add in WebUiController**
  In `stremio_catalog_provider/controller/web_ui_controller.py`:
  * Aggiungere la rotta alle API route in `_register_routes`:
    `self.router.add_api_route("/media/add", self.media_add, methods=["GET"], response_class=HTMLResponse)`
  * Implementare la funzione:
    ```python
    async def media_add(self, request: Request, credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> Any:
        self.verify_credentials(credentials)
        return self.templates.TemplateResponse(
            request,
            "media_add.html",
            {
                "active_page": "media"
            }
        )
    ```

- [ ] **Step 2: Creare il template templates/media_add.html**
  Creare il file `templates/media_add.html` copiando la card TMDB e adattandola:
  ```html
  {% extends "base.html" %}

  {% block title %}Aggiungi Media - Stremio Catalog{% endblock %}

  {% block content %}
  <div class="header">
      <div class="header-title">
          <h1>Aggiungi Nuovo Media</h1>
          <p><a href="/media" style="color:var(--accent); text-decoration:none;">&larr; Torna alla lista</a></p>
      </div>
  </div>

  <div class="card">
      <div class="card-title">Cerca su TMDB</div>
      <div style="display:flex; gap:15px; margin-bottom: 20px;">
          <input type="text" id="tmdb-search-query" class="form-control" placeholder="Cerca film o serie TV su TMDB...">
          <select id="tmdb-search-type" class="form-control" style="width: 150px;">
              <option value="movie">Film</option>
              <option value="series">Serie TV</option>
          </select>
          <button class="btn" onclick="searchTMDB()">Cerca</button>
      </div>
      <div id="tmdb-results" style="display:none;" class="file-list"></div>
  </div>
  {% endblock %}

  {% block scripts %}
  <script>
  function searchTMDB() {
      var query = document.getElementById("tmdb-search-query").value;
      var type = document.getElementById("tmdb-search-type").value;
      if (!query) return;

      fetch("/api/tmdb/search?query=" + encodeURIComponent(query) + "&type=" + type)
          .then(res => res.json())
          .then(data => {
              var container = document.getElementById("tmdb-results");
              container.innerHTML = "";
              container.style.display = "block";

              if (data.results && data.results.length > 0) {
                  data.results.forEach(function(item) {
                      var div = document.createElement("div");
                      div.className = "file-item";

                      var title = item.title || item.name;
                      var date = item.release_date || item.first_air_date || "";
                      var year = date ? date.substring(0, 4) : "";

                      div.innerHTML = `
                          <div class="file-name"><strong>${title}</strong> (${year})</div>
                          <button class="btn btn-success" onclick="addFromTMDB(${item.id}, '${type}')">Importa</button>
                      `;
                      container.appendChild(div);
                  });
              } else {
                  container.innerHTML = "<div class='file-name'>Nessun risultato trovato.</div>";
              }
          });
  }

  function addFromTMDB(id, type) {
      fetch("/api/media", {
          method: "POST",
          headers: {
              "Content-Type": "application/json"
          },
          body: JSON.stringify({ tmdb_id: id, type: type })
      })
      .then(res => res.json())
      .then(data => {
          if (data.status === "ok") {
              alert("Media importato con successo!");
              window.location.href = "/media";
          } else {
              alert("Errore nell'importazione: " + data.error);
          }
      });
  }
  </script>
  {% endblock %}
  ```

- [ ] **Step 3: Aggiornare templates/media.html**
  Rimuovere la prima card (righe 13-24 in `templates/media.html`).
  Modificare il titolo in alto aggiungendo il bottone:
  ```html
  <div class="header">
      <div class="header-title">
          <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
              <h1>Gestione Media</h1>
              <a href="/media/add" class="btn" style="text-decoration:none;">Aggiungi Media</a>
          </div>
          <p>Naviga all'interno dei film e serie TV del tuo catalogo.</p>
      </div>
  </div>
  ```

- [ ] **Step 4: Eseguire i test e verificare la rotta**
  Eseguire `python -m pytest tests/controller/test_web_ui_auth.py` per accertarsi che le nuove rotte web richiedano l'autenticazione.

---

### Task 5: Modifica Torrent & Re-mapping Automatico dei File

**Files:**
* Modify: `stremio_catalog_provider/controller/web_ui_controller.py`
* Modify: `stremio_catalog_provider/controller/api_controller.py`
* Modify: `templates/torrents.html`
* Create: `templates/torrent_edit.html`
* Modify: `tests/controller/test_web_ui_auth.py`

**Interfaces:**
* Consumes: `TorrentRepository`, `FileMappingRepository`, `EpisodeRepository`, `PTN`
* Produces:
  * Rotta Web: `GET /torrents/{torrent_id}/edit`
  * API: `PUT /api/torrents/{torrent_id}`

- [ ] **Step 1: Scrivere test per PUT /api/torrents/{torrent_id}**
  In `tests/controller/test_web_ui_auth.py`, aggiungere test per la modifica del torrent:
  ```python
  def test_update_torrent_endpoint(client, session) -> None:
      # Creare torrent di test nel DB
      # Eseguire chiamata PUT a /api/torrents/{id} con autorizzazione basic auth
      # Verificare che titolo e predefined_media_item_id siano aggiornati correttamente
      pass # L'implementazione completa del test sarà scritta inline
  ```

- [ ] **Step 2: Aggiungere rotte nel Web UI e API Controller**
  * In `stremio_catalog_provider/controller/web_ui_controller.py`:
    * Registrare: `self.router.add_api_route("/torrents/{torrent_id}/edit", self.torrent_edit, methods=["GET"], response_class=HTMLResponse)`
    * Implementare:
      ```python
      async def torrent_edit(self, request: Request, torrent_id: int, credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> Any:
          self.verify_credentials(credentials)
          torrent = self.torrent_repo.get_by_id(torrent_id)
          if not torrent:
              raise HTTPException(status_code=404, detail="Torrent not found")
          all_media = self.media_repo.search_local(query="")
          return self.templates.TemplateResponse(
              request,
              "torrent_edit.html",
              {
                  "active_page": "torrents",
                  "torrent": torrent,
                  "all_media": all_media
              }
          )
      ```
  * In `stremio_catalog_provider/controller/api_controller.py`:
    * Registrare: `self.router.add_api_route("/api/torrents/{torrent_id}", self.update_torrent, methods=["PUT"])`
    * Aggiungere lo schema Pydantic:
      ```python
      class TorrentUpdateRequest(BaseModel):
          title: Optional[str] = None
          predefined_media_item_id: Optional[int] = None
          remap_files: bool = False
      ```
    * Implementare `update_torrent` con logica di re-mapping automatico:
      ```python
      async def update_torrent(
          self, torrent_id: int, req: TorrentUpdateRequest, credentials: HTTPBasicCredentials = Depends(HTTPBasic())
      ) -> dict[str, Any]:
          self.verify_credentials(credentials)
          session = self.torrent_repo.get_session()
          torrent = self.torrent_repo.get_by_id(torrent_id)
          if not torrent:
              raise HTTPException(status_code=404, detail="Torrent not found")

          if req.title is not None:
              torrent.title = req.title
          
          old_media_id = torrent.predefined_media_item_id
          torrent.predefined_media_item_id = req.predefined_media_item_id
          session.commit()

          # Se richiesta la rimappatura di tutti i file a caldo
          if req.remap_files and req.predefined_media_item_id is not None:
              mappings = self.mapping_repo.get_by_torrent(torrent.id)
              media_item = self.media_repo.get_by_id(req.predefined_media_item_id)
              
              if media_item:
                  for m in mappings:
                      m.media_item_id = media_item.id
                      
                      # Se serie TV, estraiamo SxxExx e associamo l'episodio corretto
                      if media_item.type == "series":
                          parsed = self.mapping_service.parser_service.parse_filename(m.file_path.split("/")[-1])
                          if parsed["season"] is not None and parsed["episode"] is not None:
                              episode = self.episode_repo.get_or_create(
                                  media_item.id, parsed["season"], parsed["episode"]
                              )
                              m.episode_id = episode.id
                          else:
                              m.episode_id = None
                      else:
                          m.episode_id = None
                          
                  session.commit()

          return {"status": "ok"}
      ```

- [ ] **Step 3: Creare il template templates/torrent_edit.html**
  Creare `templates/torrent_edit.html` con il form di modifica:
  ```html
  {% extends "base.html" %}

  {% block title %}Modifica Torrent - Stremio Catalog{% endblock %}

  {% block content %}
  <div class="header">
      <div class="header-title">
          <h1>Modifica Torrent</h1>
          <p><a href="/torrents" style="color:var(--accent); text-decoration:none;">&larr; Torna alla lista torrent</a></p>
      </div>
  </div>

  <div class="card">
      <div class="card-title">Dettagli del Torrent</div>
      
      <div class="form-group">
          <label class="form-label" for="torrent-title">Titolo Visualizzato:</label>
          <input type="text" id="torrent-title" class="form-control" value="{{ torrent.title or '' }}" placeholder="Risoluzione titolo...">
      </div>

      <div class="form-group">
          <label class="form-label" for="predefined-media-id">Associa al Media:</label>
          <select id="predefined-media-id" class="form-control">
              <option value="">-- Nessun Media Associato --</option>
              {% for m in all_media %}
              <option value="{{ m.id }}" {% if m.id == torrent.predefined_media_item_id %}selected{% endif %}>{{ m.title }} ({{ m.year }}) - {{ 'Serie TV' if m.type == 'series' else 'Film' }}</option>
              {% endfor %}
          </select>
      </div>

      <div class="form-group" style="display:flex; align-items:center; gap:10px;">
          <input type="checkbox" id="remap-files" style="width:20px; height:20px; cursor:pointer;">
          <label for="remap-files" style="cursor:pointer; font-size:14px; color:var(--text-secondary);">Rimappa automaticamente tutti i file del torrent a questo media (ricostruisce gli episodi se Serie TV)</label>
      </div>

      <button class="btn" onclick="saveTorrent()">Salva Modifiche</button>
  </div>
  {% endblock %}

  {% block scripts %}
  <script>
  function saveTorrent() {
      var title = document.getElementById("torrent-title").value;
      var mediaId = document.getElementById("predefined-media-id").value;
      var remap = document.getElementById("remap-files").checked;

      var payload = {
          title: title || null,
          predefined_media_item_id: mediaId ? parseInt(mediaId) : null,
          remap_files: remap
      };

      fetch("/api/torrents/{{ torrent.id }}", {
          method: "PUT",
          headers: {
              "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
          if (data.status === "ok") {
              alert("Torrent aggiornato correttamente!");
              window.location.href = "/torrents";
          } else {
              alert("Errore durante l'aggiornamento: " + data.error);
          }
      });
  }
  </script>
  {% endblock %}
  ```

- [ ] **Step 4: Aggiornare templates/torrents.html**
  Aggiungere un pulsante "Modifica" di fianco ad ogni Torrent in lista per andare a `/torrents/{id}/edit`:
  Modificare riga 45 del pulsante:
  ```html
  <div style="display:flex; gap:8px;">
      {% if t.status == 'FAILED' %}
      <button class="btn btn-secondary btn-sm" onclick="retryTorrent('{{ t.info_hash }}')">Riprova</button>
      {% endif %}
      <button class="btn btn-secondary btn-sm" onclick="window.location.href='/torrents/{{ t.id }}/edit'">Modifica</button>
      <button class="btn btn-secondary btn-sm" onclick="toggleFiles('{{ t.info_hash }}')">File</button>
      <button class="btn btn-secondary btn-sm" style="background:rgba(255, 23, 68, 0.1); color:var(--danger);" onclick="deleteTorrent('{{ t.info_hash }}')">Elimina</button>
  </div>
  ```

- [ ] **Step 5: Verificare tutti i test**
  Eseguire `python -m pytest`
  Expected: Pass.
