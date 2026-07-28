# Torrent Table UI Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ottimizzare l'interfaccia utente della tabella dei torrent riducendo padding/font e integrando icone FontAwesome al posto dei testi dei pulsanti per evitare overflow.

**Architecture:** Modifiche al file di template base per includere FontAwesome da CDN, aggiornamento delle classi e dei pulsanti in `torrents.html`, e aggiunta di stili di visualizzazione responsive e di troncamento in `style.css`.

**Tech Stack:** HTML, CSS, Jinja2, Python (FastAPI/Pytest)

## Global Constraints

- Mantenere l'integrità dei commenti e dei docstring esistenti nel codice non modificato.
- Rispettare PEP 8 per eventuali script o modifiche Python.
- Mantenere il pulsante "Aggiungi" superiore come pulsante testuale.

---

### Task 1: Aggiunta dei Test di Rendering e Integrazione FontAwesome in `base.html`

**Files:**
- Create: `tests/controller/test_web_ui_views.py`
- Modify: `templates/base.html`

**Interfaces:**
- Consumes: Niente
- Produces: Test di rendering per la pagina `/torrents` e caricamento globale di FontAwesome CDN in `base.html`.

- [ ] **Step 1: Scrivere il test di rendering fallimentare**

Creare il file [test_web_ui_views.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/tests/controller/test_web_ui_views.py) con il seguente contenuto:

```python
import os
import base64
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TMDB_API_KEY"] = "test_key"
os.environ["TORRSERVER_BASE_URL"] = "http://test_torr:8090"
os.environ["BASIC_AUTH_USERNAME"] = "test_user"
os.environ["BASIC_AUTH_PASSWORD"] = "test_pass"

from stremio_catalog_provider.api import app
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.entity.base import BaseEntity
from stremio_catalog_provider.manager.db_manager import DbManager

def test_torrents_page_elements_and_layout() -> None:
    container = DefaultContainer.getInstance()
    db_manager = container.get(DbManager)
    BaseEntity.metadata.create_all(db_manager.engine)
    session = db_manager.get_session()

    from stremio_catalog_provider.entity.torrent import Torrent
    
    # Aggiunge un torrent mock per popolare la tabella
    torrent = Torrent(
        info_hash="1234567890abcdef1234567890abcdef12345678",
        magnet_url="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
        title="Test Torrent Title That Is Extremely Long to Test Truncation",
        status="FAILED"
    )
    session.add(torrent)
    session.commit()

    client = TestClient(app)
    token = base64.b64encode(b"test_user:test_pass").decode("utf-8")
    headers = {"Authorization": f"Basic {token}"}

    res = client.get("/torrents", headers=headers)
    assert res.status_code == 200
    html = res.text

    # Verifica FontAwesome CDN
    assert "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" in html

    # Verifica struttura tabella responsive
    assert "class=\"table-responsive\"" in html

    # Verifica classi colonne
    assert "class=\"col-title\"" in html
    assert "class=\"col-hash\"" in html
    assert "class=\"col-actions\"" in html

    # Verifica icone FontAwesome presenti nei pulsanti
    assert "fa-rotate-right" in html
    assert "fa-pen-to-square" in html
    assert "fa-folder-open" in html
    assert "fa-trash-can" in html
```

- [ ] **Step 2: Eseguire pytest per verificare che il test fallisca**

Eseguire:
```bash
docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py
```
Expected: FAIL dovuto all'assenza della stringa CDN di FontAwesome in `base.html` e della classe `table-responsive`.

- [ ] **Step 3: Aggiungere il link CDN di FontAwesome a `base.html`**

Modificare [base.html](file:///Users/michele/PycharmProjects/stremio-catalog-provider/templates/base.html) inserendo la CDN di FontAwesome all'interno dell'head:

```html
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {% block extra_head %}{% endblock %}
```

- [ ] **Step 4: Eseguire pytest per verificare il primo pass parziale**

Eseguire:
```bash
docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py
```
Expected: FAIL, ma l'asserzione di FontAwesome CDN deve essere superata, arrestandosi su `class="table-responsive"`.


### Task 2: Refactoring del layout e dei pulsanti in `torrents.html`

**Files:**
- Modify: `templates/torrents.html`

**Interfaces:**
- Consumes: Caricamento globale di FontAwesome da Task 1.
- Produces: Struttura HTML aggiornata in `torrents.html` con classi responsive ed icone nei pulsanti di azione.

- [ ] **Step 1: Eseguire pytest per assicurarsi che fallisca su `table-responsive`**

Eseguire:
```bash
docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py
```
Expected: FAIL su `class="table-responsive"`.

- [ ] **Step 2: Modificare `templates/torrents.html`**

Modificare [torrents.html](file:///Users/michele/PycharmProjects/stremio-catalog-provider/templates/torrents.html) per aggiornare la struttura della tabella e i relativi pulsanti:

```html
{% extends "base.html" %}

{% block title %}Torrents - Stremio Catalog{% endblock %}

{% block content %}
<div class="header">
    <div class="header-title">
        <h1>Coda Torrent</h1>
        <p>Monitora lo stato di risoluzione dei magnet ed effettua correzioni manuali.</p>
    </div>
</div>

<div class="card">
    <div class="card-title">Aggiungi Torrent Generico</div>
    <div style="display:flex; gap:15px;">
        <input type="text" id="magnet-url-generic" class="form-control" placeholder="Inserisci magnet link...">
        <button class="btn" onclick="addGenericTorrent()">Aggiungi</button>
    </div>
</div>

<div class="card">
    <div class="card-title">Torrent in Coda</div>
    <div class="table-responsive">
        <table class="torrent-table">
            <thead>
                <tr>
                    <th class="col-title">Titolo</th>
                    <th class="col-hash">Hash</th>
                    <th>Aggiunto il</th>
                    <th>Stato</th>
                    <th class="col-actions">Azioni</th>
                </tr>
            </thead>
            <tbody>
                {% for t in torrents %}
                <tr>
                    <td class="col-title"><strong>{{ t.title or 'Risoluzione titolo...' }}</strong></td>
                    <td class="col-hash"><code style="background:rgba(255,255,255,0.05); padding:4px 8px; border-radius:6px;">{{ t.info_hash }}</code></td>
                    <td>{{ t.added_at.strftime('%d/%m/%Y %H:%M') }}</td>
                    <td><span class="badge badge-{{ t.status.lower() }}">{{ t.status }}</span></td>
                    <td class="col-actions">
                        <div style="display:flex; gap:8px;">
                            {% if t.status == 'FAILED' %}
                            <button class="btn btn-secondary btn-sm" onclick="retryTorrent('{{ t.info_hash }}')" title="Riprova"><i class="fa-solid fa-rotate-right"></i></button>
                            {% endif %}
                            <button class="btn btn-secondary btn-sm" onclick="window.location.href='/torrents/{{ t.id }}/edit'" title="Modifica"><i class="fa-solid fa-pen-to-square"></i></button>
                            <button class="btn btn-secondary btn-sm" onclick="toggleFiles('{{ t.info_hash }}')" title="File contenuti"><i class="fa-solid fa-folder-open"></i></button>
                            <button class="btn btn-secondary btn-sm" style="background:rgba(255, 23, 68, 0.1); color:var(--danger);" onclick="deleteTorrent('{{ t.info_hash }}')" title="Elimina"><i class="fa-solid fa-trash-can"></i></button>
                        </div>
                    </td>
                </tr>
                <tr id="files-{{ t.info_hash }}" style="display:none; background:rgba(0,0,0,0.15);">
                    <td colspan="5">
                        <div class="file-list" id="file-list-content-{{ t.info_hash }}">
                            Caricamento file...
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

E aggiornare la funzione javascript `loadFiles` all'interno del blocco `{% block scripts %}` per utilizzare l'icona e l'attributo `title` nel pulsante "Modifica" dei file:

```javascript
                    div.innerHTML = `
                        <div class="file-name">
                            <div>\${m.file_path} <span class="file-size">(\${sizeMB} MB)</span></div>
                            <div style="font-size:13px; margin-top:4px;">\${mappingText}</div>
                        </div>
                        <button class="btn btn-secondary btn-sm" onclick="window.location.href='/remap/\${m.id}'" title="Modifica mapping"><i class="fa-solid fa-pen-to-square"></i></button>
                    `;
```

- [ ] **Step 3: Eseguire pytest per verificare che tutti i test di rendering passino**

Eseguire:
```bash
docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py
```
Expected: PASS.


### Task 3: Aggiunta delle Regole CSS per Layout Responsive e Troncamento Testi in `style.css`

**Files:**
- Modify: `static/css/style.css`

**Interfaces:**
- Consumes: Struttura aggiornata di `torrents.html`.
- Produces: CSS compilato con regole responsive per tabelle e troncamento delle colonne.

- [ ] **Step 1: Modificare `static/css/style.css`**

Modificare [style.css](file:///Users/michele/PycharmProjects/stremio-catalog-provider/static/css/style.css) sostituendo o aggiungendo i seguenti stili (indicativamente alle righe 392-441 per la sezione Torrent Table):

```css
/* Torrent list / Queue tables */
.table-responsive {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-top: 15px;
}

.torrent-table {
    width: 100%;
    border-collapse: collapse;
}

.torrent-table th, .torrent-table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
    vertical-align: middle;
}

.torrent-table th {
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 13px;
}

.torrent-table td {
    font-size: 14px;
}

/* Regole per il troncamento con ellissi (...) */
.col-title {
    max-width: 280px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.col-hash {
    max-width: 160px;
}

.col-hash code {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: middle;
    background: rgba(255, 255, 255, 0.05);
    padding: 4px 8px;
    border-radius: 6px;
}

.col-actions {
    width: 1%;
    white-space: nowrap;
}

.col-actions .btn {
    padding: 8px 12px;
}
```

- [ ] **Step 2: Eseguire l'intera suite di test del progetto**

Eseguire:
```bash
docker compose run --rm web-api pytest
```
Expected: Tutti i test (incluso quello creato in Task 1) passano con successo.
