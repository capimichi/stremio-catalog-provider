# Specifica Tecnica: Ridenominazione e Popolamento Automatico del campo Media ID nei Torrent

* **Data**: 2026-07-28
* **Stato**: In Revisione
* **Autore**: Antigravity & Michele

---

## 1. Obiettivo & Contesto

Attualmente, l'entità `Torrent` dispone della colonna facoltativa `predefined_media_item_id`. Questa colonna viene usata come override manuale per forzare l'associazione di tutti i file di un torrent a uno specifico `MediaItem`. Se un torrent viene elaborato in automatico tramite TMDB, questa colonna rimane a `NULL`, rendendo fuorviante la pagina di modifica del torrent che mostra *"Nessun Media Associato"*.

### Obiettivi:
1. Ridenominare il campo `predefined_media_item_id` in `media_id` per rendere il database e il codice più leggibili e concisi.
2. Aggiornare la migrazione originale di creazione tabella (`1002_create_torrents.py`).
3. Modificare il Background Worker in modo che, al termine del parsing automatico, salvi l'ID del primo media rilevato direttamente all'interno della colonna `media_id` del torrent (se non già popolata).
4. Aggiornare l'interfaccia di modifica torrent (`torrent_edit.html`) e i relativi test per supportare la modifica.

---

## 2. Modifiche ai File di Progetto

### 2.1 Aggiornamento Migrazione Alembic
File: [1002_create_torrents.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/alembic/versions/1002_create_torrents.py)

Sostituzione della colonna `predefined_media_item_id` con `media_id`:
```python
        sa.Column('media_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['media_id'], ['media_items.id'], ),
```

### 2.2 Aggiornamento dell'Entità Torrent
File: [torrent.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/entity/torrent.py)

Sostituzione del campo sul modello SQLAlchemy:
```python
    media_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("media_items.id"), nullable=True
    )
```

### 2.3 Aggiornamento del Background Worker
File: [torrent_process_service.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/service/torrent_process_service.py)

* Lettura del media manuale tramite `torrent.media_id` anziché `torrent.predefined_media_item_id`.
* Al termine del ciclo di mapping dei file, assegnazione del primo media rilevato a `torrent.media_id` se quest'ultimo è vuoto:
```python
            # In fondo al metodo process_next_torrent, prima di completare la transazione:
            mapped_ids = [m.media_item_id for m in torrent.mappings if m.media_item_id is not None]
            if mapped_ids and not torrent.media_id:
                torrent.media_id = mapped_ids[0]
```

### 2.4 Aggiornamento del Torrent Service
File: [torrent_service.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/service/torrent_service.py)

Aggiornamento della firma e del dizionario di creazione torrent:
```python
    # Nel metodo add_torrent:
    torrent = Torrent(
        info_hash=info_hash,
        magnet_url=magnet_url,
        title=parsed_title,
        status="QUEUED",
        media_id=media_id
    )
```

### 2.5 Aggiornamento dei Controller (API e Web UI)
File: [api_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/api_controller.py)
* Aggiornamento del modello Pydantic `UpdateTorrentRequest`:
  ```python
  class UpdateTorrentRequest(BaseModel):
      title: Optional[str] = None
      media_id: Optional[int] = None
      remap_files: bool = False
  ```
* Aggiornamento dell'endpoint `update_torrent` per leggere `req.media_id`.

File: [web_ui_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/web_ui_controller.py)
* Nessun cambio logico richiesto nel controller Web UI oltre all'adeguamento delle referenze a `media_id` o `torrent.media_id`.

### 2.6 Aggiornamento del Template di Modifica
File: [torrent_edit.html](file:///Users/michele/PycharmProjects/stremio-catalog-provider/templates/torrent_edit.html)

* Aggiornamento della condizione di pre-selezione nel dropdown:
  ```html
  <option value="{{ m.id }}" {% if m.id == torrent.media_id %}selected{% endif %}>...
  ```
* Ridenominazione del campo inviato in Ajax da `predefined_media_item_id` a `media_id`.

---

## 3. Strategia di Test & Validazione

1. **Rebuild del Database**:
   * Eseguire `docker compose down -v && docker compose up -d` per ricostruire il database locale MariaDB partendo dalle migrazioni modificate.
2. **Aggiornamento Test Automatici**:
   * Sostituire le occorrenze di `predefined_media_item_id` con `media_id` nei file di test:
     * `tests/controller/test_web_ui_auth.py`
     * `tests/service/test_services.py`
     * `tests/service/test_torrent_process_service.py`
   * Eseguire `docker compose run --rm web-api pytest` per accertarsi che tutti i test passino regolarmente.
