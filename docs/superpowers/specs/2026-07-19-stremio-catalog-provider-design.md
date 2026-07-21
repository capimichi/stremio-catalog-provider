# Specifica Tecnica: Stremio Custom Catalog Provider

* **Data**: 2026-07-19
* **Stato**: Approvato (Fase Brainstorming completata)
* **Autore**: Antigravity & Michele
* **Repository di Riferimento per la Backbone**: [/Users/michele/PycharmProjects/rivo-drome/](file:///Users/michele/PycharmProjects/rivo-drome/)

---

## 1. Obiettivo & Ambito

Il progetto ha lo scopo di realizzare un **fornitore di catalogo Stremio personalizzato** in Python. Il sistema riceve magnet link o file torrent dall'utente, ne analizza il contenuto tramite **TorrServer** e associa i singoli file video ai metadati di film e serie TV tramite **TMDB**. 

Il backend espone le rotte compatibili con il protocollo Addon di Stremio per lo streaming direto e fornisce un'**Interfaccia Web Admin** protetta per monitorare la coda, inserire nuovi elementi e gestire manualmente le mappature dei file video.

---

## 2. Architettura & Struttura delle Cartelle

L'architettura segue il pattern **Clean Architecture** basato sull'iniezione delle dipendenze (Dependency Injection) tramite la libreria `injector`. 

I template HTML e le risorse statiche sono posizionati a livello di root (fuori dal namespace Python) per mantenere pulito il codice sorgente del pacchetto.

```text
stremio-catalog-provider/
├── alembic.ini                   # Configurazione per le migrazioni DB
├── alembic/                      # Script di migrazione generati
├── docker-compose.yml            # Orchestrazione container Docker
├── Dockerfile                    # Dockerfile unico per API e Worker
├── requirements.txt              # Dipendenze del progetto
├── README.md                     # Documentazione generale
│
├── templates/                    # Template HTML Jinja2 (a livello root)
│   ├── base.html                 # Layout di base con sidebar
│   ├── dashboard.html            # Statistiche e pulsante installazione Stremio
│   ├── media.html                # Griglia dei film/serie e ricerca TMDB
│   ├── media_details.html        # Dettaglio media, trama e torrent associati
│   ├── torrents.html             # Coda di caricamento dei torrent
│   └── remap.html                # Interfaccia di rimappatura manuale
│
├── static/                       # File statici CSS e JS (a livello root)
│   └── css/
│       └── style.css             # CSS personalizzato (Dark Mode, Glassmorphism)
│
└── stremio_catalog_provider/     # Namespace principale del pacchetto
    ├── __init__.py
    ├── api.py                    # Entrypoint applicazione FastAPI
    ├── cli.py                    # Entrypoint click per la CLI ed esecuzione worker
    │
    ├── client/                   # Chiamate alle API esterne
    │   ├── tmdb_client.py        # Client HTTPX per TMDB (ricerche, metadati)
    │   └── torrserver_client.py  # Client HTTPX per gestire TorrServer (Basic Auth supportato)
    │
    ├── command/                  # Comandi Click CLI
    │   ├── abstract_command.py   # Classe astratta base per i comandi
    │   ├── worker_command.py     # Comando worker per il polling della coda
    │   └── import_command.py     # Comando CLI per importare torrent sincroni
    │
    ├── config/                   # Classi di configurazione dei servizi
    │   ├── tmdb_config.py        # TMDB API Key
    │   └── torrserver_config.py  # URL TorrServer, credenziali Basic Auth
    │
    ├── container/                # Configurazione Dependency Injection
    │   └── default_container.py  # Configurazione dell'Injector e binding
    │
    ├── controller/               # FastAPI Router
    │   ├── stremio_controller.py # Rotte Addon Stremio (pubbliche)
    │   ├── web_ui_controller.py  # Rotte Web UI (protette da Basic Auth)
    │   └── api_controller.py     # Rotte API JSON di amministrazione (protette)
    │
    ├── entity/                   # Modelli SQLAlchemy (ORM)
    │   ├── base.py               # BaseEntity comune
    │   ├── torrent.py            # Record del torrent caricato
    │   ├── media_item.py         # Film o Serie TV salvati localmente
    │   ├── episode.py            # Record del singolo episodio (per le serie)
    │   └── file_mapping.py       # Associazione file TorrServer -> Episodio/Film
    │
    ├── manager/                  # Gestori globali
    │   └── db_manager.py         # Inizializzazione e sessioni del DB
    │
    ├── repository/               # Classi CRUD per il database
    │   ├── torrent_repository.py
    │   ├── media_item_repository.py
    │   ├── episode_repository.py
    │   └── file_mapping_repository.py
    │
    └── service/                  # Logica di business
        ├── torrent_service.py    # Gestione logica dei Torrent (aggiunta, rimozione, stato, retry)
        ├── media_item_service.py # Gestione logica dei Media (catalogo, dettagli, TMDB import)
        ├── file_mapping_service.py # Gestione logica delle mappature e correzioni manuali
        ├── torrent_parser_service.py # Parsing dei nomi file video con PTN
        ├── torrent_process_service.py # Worker coordinator per il processing dei torrent
        └── stremio_service.py    # Trasformazione dati per endpoint pubblici Stremio
```

---

## 3. Modello dei Dati (Database MariaDB)

### 3.1 `Torrent`
Rappresenta il file torrent o magnet inserito nel sistema.
* `info_hash` (PK, String): Hash univoco del torrent.
* `magnet_url` (Text): Il link magnetico originale.
* `title` (String): Nome del torrent rilevato.
* `status` (Enum: `QUEUED`, `PROCESSING`, `PROCESSED`, `FAILED`): Stato dell'elaborazione.
* `error_message` (Text, Nullable): Dettaglio dell'eventuale errore.
* `added_at` (DateTime): Data di inserimento.
* `processed_at` (DateTime, Nullable): Data di fine analisi.
* `predefined_media_item_id` (FK su `MediaItem.id`, Nullable): Se impostato dall'utente, pre-associa il torrent a un film/serie specifico bypassando la ricerca automatica di TMDB.

### 3.2 `MediaItem`
Film o Serie TV con metadati recuperati da TMDB.
* `id` (PK, Integer)
* `imdb_id` (String, Unique, Index): ID ufficiale IMDb (es. `tt0949578`), fondamentale per Stremio.
* `tmdb_id` (Integer, Nullable): ID TMDB per arricchimento dati.
* `type` (Enum: `movie`, `series`): Tipo di contenuto.
* `title` (String): Titolo ufficiale pulito.
* `year` (Integer): Anno di uscita.
* `description` (Text, Nullable): Trama del film o della serie.
* `poster_url` (String, Nullable): URL assoluto dell'immagine di copertina.
* `background_url` (String, Nullable): URL assoluto dell'immagine di sfondo.

### 3.3 `Episode`
Rappresenta un singolo episodio, collegato solo se `MediaItem.type = 'series'`.
* `id` (PK, Integer)
* `media_item_id` (FK su `MediaItem.id`)
* `season` (Integer): Numero della stagione.
* `episode` (Integer): Numero dell'episodio.
* `title` (String, Nullable): Titolo dell'episodio.

### 3.4 `FileMapping`
Associa ciascun file video interno al torrent con l'entità film o episodio corretta.
* `id` (PK, Integer)
* `torrent_hash` (FK su `Torrent.info_hash`)
* `file_index` (Integer): Indice numerico del file restituito da TorrServer.
* `file_path` (String): Percorso relativo del file all'interno del torrent.
* `file_size` (BigInteger): Dimensione in byte del file.
* `media_item_id` (FK su `MediaItem.id`, Nullable): Impostato se il torrent è mappato a un film.
* `episode_id` (FK su `Episode.id`, Nullable): Impostato se mappato ad un episodio specifico.
* `manually_corrected` (Boolean, Default `False`): Se `True`, indica che l'utente ha modificato manualmente la mappatura (impedisce al worker di sovrascriverla).

---

## 4. Logica del Worker e Gestione Errori/Timeout

Il Background Worker viene eseguito come comando CLI continuo:
`python -m stremio_catalog_provider.cli worker`

### 4.1 Processo di Polling Atomico
Il worker esegue ciclicamente la query atomica su MariaDB:
```sql
SELECT * FROM torrents WHERE status = 'QUEUED' ORDER BY added_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED;
```
Se trova un torrent, aggiorna immediatamente lo stato a `PROCESSING` e committa la transazione per liberare il DB ad altri worker concorrenti.

### 4.2 Integrazione TorrServer & Gestione dei Timeout
1. **Invio e Risoluzione**: Il worker aggiunge il magnet a TorrServer tramite chiamata POST. Sulle chiamate HTTPX è impostato un timeout di connessione e lettura minimo di **30 secondi**.
2. **Polling DHT**: TorrServer deve contattare i peer per risolvere la lista file. Il worker interroga TorrServer ogni 5 secondi.
3. **Timeout DHT**: Se TorrServer non restituisce la lista dei file entro **5 minuti** (300 secondi):
   * Invia un comando a TorrServer per rimuovere il torrent (evitando accumulo di torrent in stallo).
   * Imposta lo stato del `Torrent` su `FAILED` con errore: *"Timeout: impossibile risolvere i metadati del torrent (mancanza di seed/peer)."*
   * Libera il worker per il successivo torrent in coda.
4. **Basic Auth**: Il client gestirà l'autenticazione HTTP Basic verso TorrServer leggendo `TORRSERVER_USERNAME` e `TORRSERVER_PASSWORD` dalle variabili d'ambiente.

### 4.3 Algoritmo di Mappatura (Parsing & TMDB)
1. Recupera la lista dei file da TorrServer.
2. Filtra i file video escludendo estensioni non multimediali (`.txt`, `.nfo`, `.srt`, ecc.).
3. Per ogni file video, usa il parser `PTN` tramite `TorrentParserService` per estrarre Titolo, Stagione ed Episodio.
4. **Se `predefined_media_item_id` è impostato**:
   * Salta la ricerca TMDB globale.
   * Associa i file video direttamente a quel `MediaItem` (creando i record `Episode` nel DB se non esistono).
5. **Se non impostato**:
   * Esegue una ricerca su TMDB tramite `TMDbClient` usando il nome estratto.
   * Se trova corrispondenza, inserisce/aggiorna il `MediaItem` (con poster, sfondo, descrizione) e vi mappa i file.
   * Se non trova corrispondenza, imposta il torrent a `FAILED` (l'utente dovrà correggerlo manualmente tramite la schermata di remap).

---

## 5. Specifiche Interfaccia Utente Web Admin

L'interfaccia utente web presenta un layout a sidebar fissa a sinistra e un design moderno (Dark Mode, Glassmorphism, animazioni fluide e font *Inter*).

### 5.1 Dashboard (`dashboard.html`)
* **Card statistiche**: Totale media nel catalogo, stato del worker, torrent in coda.
* **Sezione Installazione Stremio**:
  * Pulsante verde **"Installa Addon su Stremio"** che apre l'URL con schema `stremio://<host>/manifest.json` per l'installazione immediata sul client dell'utente.
  * Campo di testo "copia con un click" con l'URL completo del manifest HTTP.

### 5.2 Pagina Media (`media.html`)
* Griglia responsive di poster dei `MediaItem` salvati localmente.
* Barra di ricerca locale e filtro rapido (Tutti / Film / Serie TV).
* Pulsante **"Aggiungi Media"**: Apre una casella di ricerca TMDB in tempo reale. Consente di selezionare un film/serie non ancora presente nel sistema per salvarne il metadato principale nel database (permettendo poi di aggiungervi torrent pre-mappati).

### 5.3 Dettaglio Media (`media_details.html`)
* Mostra il poster del media, il titolo, l'anno, e la trama caricata da TMDB.
* Elenca tutti i torrent associati a questo media, con il loro stato.
* Pulsante **"Aggiungi Torrent"**: Apre il form con l'ID di questo media pre-compilato, forzando la mappatura diretta e bypassando la ricerca automatica di TMDB sul worker.

### 5.4 Pagina Torrents (`torrents.html`)
* Tabella cronologica dei torrent aggiunti, con badge di stato colorati (pulsanti di Retry se fallito, ed Elimina).
* Cliccando su un torrent, si espande una **tabella interna con l'elenco dei file video contenuti**.
* Per ciascun file viene mostrato il percorso, la dimensione e la mappatura corrente (es. *"Stagione 1, Episodio 2"*).
* Accanto a ogni file c'è un pulsante **"Modifica"** per alterare/rimappare manualmente l'associazione del singolo file inline tramite un piccolo modulo.

---

## 6. Integrazione Stremio (Addon API)

Il backend FastAPI espone gli endpoint pubblici Stremio:
1. **/manifest.json**: Ritorna le info dell'addon, supportando i cataloghi dei media locali ed esponendo i filtri per IMDb ID.
2. **/catalog/{type}/{id}.json**: Ritorna la lista dei nostri `MediaItem` (sotto forma di meta-oggetti Stremio) per visualizzarli nella scheda addon.
3. **/meta/{type}/{id}.json**: Ritorna i dettagli completi del media (inclusa la lista delle stagioni/episodi costruita leggendo le tabelle `Episode` e `FileMapping`).
4. **/stream/{type}/{id}.json**:
   * Per un film: cerca il `FileMapping` associato all'IMDb ID del film.
   * Per un episodio: cerca il `FileMapping` associato all'ID `imdb_id:season:episode`.
   * Restituisce l'URL di streaming diretto verso l'endpoint HTTP di TorrServer per il `file_index` corretto:
     `{TORRSERVER_BASE_URL}/stream/{torrent_title}?link={file_index}&play` (se presente autenticazione, il server FastAPI può anche fungere da reindirizzatore / proxy di autenticazione per fornire stream validi al client).
