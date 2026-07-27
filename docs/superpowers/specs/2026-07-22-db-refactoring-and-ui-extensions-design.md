# Specifica Tecnica: Refactoring Database, Risoluzione Titoli e Miglioramenti Web UI

* **Data**: 2026-07-22
* **Stato**: In Revisione
* **Autori**: Antigravity & Michele

---

## 1. Obiettivo & Contesto

Questa specifica descrive le modifiche necessarie per migliorare la struttura del database, ottimizzare la stabilità del background worker e potenziare l'esperienza utente dell'interfaccia di amministrazione del catalogo.

### Obiettivi Principali:
1. **Refactoring del Database**: Introdurre un ID primario numerico auto-incrementale nella tabella `torrents` e aggiornare la chiave esterna di `file_mappings` affinché punti all'ID e non all'hash.
2. **Risoluzione Automatica dei Titoli**: Estrarre il titolo dei torrent da TorrServer o, in alternativa, utilizzare un meccanismo di fallback con la libreria `PTN` sul nome del primo file video.
3. **Miglioramenti UI/UX**:
   * Separare la sezione di inserimento media da TMDB in una pagina a sé stante (`/media/add`).
   * Creare una pagina di modifica delle informazioni del singolo torrent (`/torrents/{torrent_id}/edit`) per consentire all'utente di correggere il titolo o ri-associare l'intero torrent a un altro film o serie TV (con re-mapping automatico di tutti i file video contenuti).

---

## 2. Modifiche allo Schema del Database & Migrazioni

Essendo il progetto in fase embrionale, le modifiche verranno integrate direttamente nei file di migrazione esistenti per evitare la creazione di nuove migrazioni ridondanti.

### 2.1 Modello `Torrent`
File: [torrent.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/entity/torrent.py)

* Aggiunta del campo `id` come chiave primaria auto-incrementale.
* Spostamento di `info_hash` a campo univoco, indicizzato e obbligatorio (`unique=True`, `index=True`, `nullable=False`).

```python
class Torrent(BaseEntity):
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
```

### 2.2 Modello `FileMapping`
File: [file_mapping.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/entity/file_mapping.py)

* Sostituzione di `torrent_hash` con `torrent_id` (chiave esterna collegata a `torrents.id`).
* Definizione della relazione `torrent` verso l'entità `Torrent`.
* Aggiunta di una property `@property def torrent_hash` per retrocompatibilità con l'integrazione di streaming Stremio, che restituisce `self.torrent.info_hash`.

```python
class FileMapping(BaseEntity):
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

### 2.3 Modifiche ai File di Migrazione Alembic
* **[1002_create_torrents.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/alembic/versions/1002_create_torrents.py)**:
  * Modificare `sa.Column('info_hash', sa.String(length=40), nullable=False)` in `sa.Column('info_hash', sa.String(length=40), nullable=False, unique=True)`.
  * Aggiungere `sa.Column('id', sa.Integer(), autoincrement=True, nullable=False)`.
  * Sostituire `sa.PrimaryKeyConstraint('info_hash')` con `sa.PrimaryKeyConstraint('id')`.
* **[1004_create_file_mappings.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/alembic/versions/1004_create_file_mappings.py)**:
  * Modificare la colonna `torrent_hash` in `torrent_id` (`sa.Integer()`).
  * Sostituire `sa.ForeignKeyConstraint(['torrent_hash'], ['torrents.info_hash'], ondelete='CASCADE')` con `sa.ForeignKeyConstraint(['torrent_id'], ['torrents.id'], ondelete='CASCADE')`.

---

## 3. Logica del Worker e Risoluzione Titoli

### 3.1 Aggiornamento del Client TorrServer
File: [torrserver_client.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/client/torrserver_client.py)

Aggiunta del metodo `get_torrent` per recuperare i dettagli completi del torrent da TorrServer:
```python
    def get_torrent(self, info_hash: str) -> dict[str, Any]:
        """Recupera le informazioni complete di un torrent da TorrServer."""
        endpoint = f"{self.config.base_url}/torrents"
        payload = {"action": "get", "hash": info_hash}
        response = httpx.post(endpoint, json=payload, auth=self.auth, timeout=30.0)
        response.raise_for_status()
        return response.json()
```

### 3.2 Aggiornamento di `TorrentProcessService`
File: [torrent_process_service.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/service/torrent_process_service.py)

1. Nel ciclo di polling del worker, viene invocato `get_torrent` invece di `get_torrent_files`.
2. Estrazione del titolo del torrent (`title`) restituito da TorrServer.
3. **Meccanismo di Fallback PTN**: Se il titolo restituito da TorrServer è nullo o vuoto, il worker cercherà il primo file video nel torrent. Applicherà la libreria `PTN` sul nome del file per estrarre un titolo pulito.
4. Salvataggio del titolo nel database e commit immediato per rendere visibile il titolo in tempo reale nella dashboard e nella coda torrent.

---

## 4. Modifiche UI e Controller Web / API

### 4.1 Aggiunta Media da TMDB (`/media/add`)
* **Controller**: In [web_ui_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/web_ui_controller.py), creiamo la rotta `GET /media/add` che renderizza il template `media_add.html`.
* **Template**:
  * Modifichiamo `media.html` rimuovendo la card di ricerca TMDB in alto e posizionando un pulsante "Aggiungi Media" (collegato a `/media/add`) di fianco al titolo "Gestione Media".
  * Creiamo `media_add.html` contenente solo la barra di ricerca TMDB e la lista dei risultati con pulsante "Importa".

### 4.2 Pagina di Modifica Dettagli Torrent (`/torrents/{torrent_id}/edit`)
* **Controller Web**: In `web_ui_controller.py`, aggiungiamo la rotta `GET /torrents/{torrent_id}/edit` per visualizzare il pannello di modifica del torrent. Recupera il torrent per ID e la lista di tutti i `MediaItem` locali.
* **Template `torrent_edit.html`**:
  * Campo per modificare manualmente il `title` del torrent.
  * Dropdown per scegliere il `MediaItem` da associare a livello globale (`predefined_media_item_id`).
  * Checkbox: *"Applica modifiche a tutti i file video del torrent (rimappa i file al nuovo media e reimposta gli episodi)"*.
* **Controller API**: In [api_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/api_controller.py), aggiungiamo la rotta `PUT /api/torrents/{torrent_id}`:
  * Aggiorna il titolo del torrent e il `predefined_media_item_id`.
  * Se la checkbox `remap_files` è attiva:
    * Aggiorna tutti i record `FileMapping` legati a questo torrent impostando il nuovo `media_item_id`.
    * Se il nuovo media è una **serie TV**, il backend scansiona i percorsi dei file tramite `PTN` per estrarre stagione ed episodio, crea i record `Episode` mancanti nel DB, e associa i mapping a questi ultimi.
    * Se il nuovo media è un **film**, resetta `episode_id` a `None` e associa direttamente a `media_item_id`.

---

## 5. Aggiornamento dei Repository, Servizi e Test

### 5.1 Repository e Servizi
* Tutti i repository (`TorrentRepository`, `FileMappingRepository`) e i relativi test verranno aggiornati per supportare le nuove join basate su `torrent_id` anziché `torrent_hash`.
* `TorrentRepository.get_by_hash(info_hash)` continuerà ad esistere ma eseguirà una query filtrando sul campo indicizzato `info_hash` invece della chiave primaria.
* `TorrentService` gestirà l'inserimento verificando la preesistenza del torrent tramite l'hash.

### 5.2 Test Unitari
* Tutti i test presenti in `tests/` verranno eseguiti e adattati per riflettere le nuove relazioni del database.
