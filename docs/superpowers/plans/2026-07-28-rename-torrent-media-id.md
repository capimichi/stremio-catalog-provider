# Rename Torrent Media ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ridenominare `predefined_media_item_id` in `media_id` sul database e in tutto il codice, ed allineare il worker per scrivere il media_id rilevato automaticamente sui torrent al termine del parsing.

**Architecture:** Modifiche alla migrazione originale Alembic, all'entità Torrent, a TorrentProcessService e TorrentService, ai controller API e UI, al template di modifica torrent, e allineamento completo della suite di test.

**Tech Stack:** Python (SQLAlchemy, Alembic, FastAPI, Pydantic, Pytest), HTML/Jinja2

## Global Constraints

- Mantenere l'integrità dei commenti e dei docstring esistenti nel codice non modificato.
- Rispettare PEP 8 per tutte le modifiche Python.
- Ricostruire il database docker locale per applicare la migrazione pulita.

---

### Task 1: Database Migration & SQLAlchemy Model Update

**Files:**
- Modify: `alembic/versions/1002_create_torrents.py`
- Modify: `stremio_catalog_provider/entity/torrent.py`

**Interfaces:**
- Consumes: Niente
- Produces: Database schema e modello SQLAlchemy Torrent aggiornati con `media_id`.

- [ ] **Step 1: Modificare il file di migrazione `1002_create_torrents.py`**

Modificare [1002_create_torrents.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/alembic/versions/1002_create_torrents.py) sostituendo `predefined_media_item_id` con `media_id` alle righe 29-30:

```python
        sa.Column('media_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['media_id'], ['media_items.id'], ),
```

- [ ] **Step 2: Modificare il modello `torrent.py`**

Modificare [torrent.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/entity/torrent.py) sostituendo `predefined_media_item_id` con `media_id` alle righe 24-26:

```python
    media_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("media_items.id"), nullable=True
    )
```

- [ ] **Step 3: Ricostruire il database Docker**

Eseguire i comandi per distruggere i volumi correnti e riavviare i container, in modo che Alembic applichi la nuova migrazione da zero:
```bash
docker compose down -v
docker compose up -d db
```
Attendere che il db sia pronto.


### Task 2: Service Layer Update (Torrent Services)

**Files:**
- Modify: `stremio_catalog_provider/service/torrent_process_service.py`
- Modify: `stremio_catalog_provider/service/torrent_service.py`

**Interfaces:**
- Consumes: Modello Torrent aggiornato con `media_id`.
- Produces: Logica del background worker che salva automaticamente `media_id` al termine del parsing.

- [ ] **Step 1: Modificare `torrent_process_service.py`**

Modificare [torrent_process_service.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/service/torrent_process_service.py) alle righe 97-98 per leggere `media_id`:

```python
                media_item = None
                if torrent.media_id:
                    media_item = self.media_repo.get_by_id(torrent.media_id)
```

E aggiungere in fondo al metodo `process_next_torrent` (indicativamente prima di `torrent.status = "PROCESSED"`) l'assegnazione automatica del `media_id` dai file mappati:

```python
            # Salva il primo media_item_id rilevato dai file se non è già presente un media_id
            mapped_ids = [m.media_item_id for m in torrent.mappings if m.media_item_id is not None]
            if mapped_ids and not torrent.media_id:
                torrent.media_id = mapped_ids[0]

            torrent.status = "PROCESSED"
```

- [ ] **Step 2: Modificare `torrent_service.py`**

Modificare [torrent_service.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/service/torrent_service.py) alle righe 24-28 per usare `media_id`:

```python
                info_hash=info_hash,
                magnet_url=magnet_url,
                title=parsed_title,
                status="QUEUED",
                media_id=media_id
```


### Task 3: Controller and HTML Template Update

**Files:**
- Modify: `stremio_catalog_provider/controller/api_controller.py`
- Modify: `stremio_catalog_provider/controller/web_ui_controller.py`
- Modify: `templates/torrent_edit.html`

**Interfaces:**
- Consumes: Modello e logica aggiornati da Task 1 e 2.
- Produces: API ed interfaccia utente di modifica allineate con `media_id`.

- [ ] **Step 1: Modificare `api_controller.py`**

Modificare [api_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/api_controller.py):
1. Nel modello `UpdateTorrentRequest` sostituire `predefined_media_item_id` con `media_id` (riga 35):
   ```python
   class UpdateTorrentRequest(BaseModel):
       title: Optional[str] = None
       media_id: Optional[int] = None
       remap_files: bool = False
   ```
2. Nel metodo `update_torrent` sostituire le righe 218-225:
   ```python
           torrent.media_id = req.media_id
           if req.title:
               torrent.title = req.title
   
           if req.remap_files and req.media_id is not None:
               media_item = self.media_repo.get_by_id(req.media_id)
   ```

- [ ] **Step 2: Modificare `web_ui_controller.py`**

Verificare che non vi siano riferimenti residui a `predefined_media_item_id` in [web_ui_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/web_ui_controller.py).

- [ ] **Step 3: Modificare `templates/torrent_edit.html`**

Modificare [torrent_edit.html](file:///Users/michele/PycharmProjects/stremio-catalog-provider/templates/torrent_edit.html):
1. Riga 26, sostituire il confronto con `torrent.media_id`:
   ```html
   <option value="{{ m.id }}" {% if m.id == torrent.media_id %}selected{% endif %}>{{ m.title }} ({{ m.year }}) - {{ 'Serie TV' if m.type == 'series' else 'Film' }}</option>
   ```
2. Riga 49, aggiornare il payload javascript inviato in Ajax:
   ```javascript
           media_id: mediaId ? parseInt(mediaId) : null,
   ```


### Task 4: Pytest Suite Alignment and Final Verification

**Files:**
- Modify: `tests/controller/test_web_ui_auth.py`
- Modify: `tests/service/test_services.py`
- Modify: `tests/service/test_torrent_process_service.py`

**Interfaces:**
- Consumes: Tutto il codice aggiornato nei precedenti task.
- Produces: Suite di test funzionante ed esecuzione verde.

- [ ] **Step 1: Modificare `tests/controller/test_web_ui_auth.py`**

Modificare [test_web_ui_auth.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/tests/controller/test_web_ui_auth.py) sostituendo `predefined_media_item_id` con `media_id` alle righe 84, 98, 115 e 118:

```python
    torrent = Torrent(info_hash="hashupdate", magnet_url="magnetupdate", title="Original Title", status="QUEUED", media_id=None)
```
```python
    payload = {
        "title": "New Title",
        "media_id": 10,
        "remap_files": True
    }
```
```python
    assert updated_torrent.media_id == 10
    updated_mapping = session.query(FileMapping).filter_by(id=mapping.id).first()
    assert updated_mapping.media_item_id == 10
```

- [ ] **Step 2: Modificare `tests/service/test_services.py`**

Modificare [test_services.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/tests/service/test_services.py) sostituendo `predefined_media_item_id` con `media_id` alle righe 38 e 43:

```python
    assert torrent.media_id == 42
```
```python
    assert again.media_id == 42
```

- [ ] **Step 3: Modificare `tests/service/test_torrent_process_service.py`**

Modificare [test_torrent_process_service.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/tests/service/test_torrent_process_service.py) sostituendo `predefined_media_item_id` con `media_id` alla riga 31 e aggiungendo un test che verifichi il popolamento automatico del `media_id` al termine del parsing.

- [ ] **Step 4: Eseguire la suite di test completa**

Eseguire:
```bash
docker compose run --rm web-api pytest
```
Expected: PASS su tutti i 28/29 test.
