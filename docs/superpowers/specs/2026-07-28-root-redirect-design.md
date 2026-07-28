# Specifica Tecnica: Reindirizzamento da Root a Dashboard

* **Data**: 2026-07-28
* **Stato**: In Revisione
* **Autore**: Antigravity & Michele

---

## 1. Obiettivo & Contesto

Attualmente, l'applicazione non espone alcuna rotta sulla radice (`/`). Visitando l'indirizzo root del server, viene restituito un errore `404 Not Found`.

### Obiettivo:
Aggiungere un reindirizzamento automatico (`RedirectResponse`) dalla rotta root `/` verso la dashboard amministrativa `/dashboard`.

---

## 2. Modifiche ai File di Progetto

### 2.1 Aggiornamento del Web UI Controller
File: [web_ui_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/web_ui_controller.py)

1. Aggiunta dell'importazione di `RedirectResponse`:
   ```python
   from fastapi.responses import HTMLResponse, RedirectResponse
   ```
2. Registrazione della rotta `/` in `_register_routes`:
   ```python
   self.router.add_api_route("/", self.root_redirect, methods=["GET"])
   ```
3. Definizione del metodo `root_redirect`:
   ```python
   async def root_redirect(self) -> RedirectResponse:
       """Redirects root path to dashboard page."""
       return RedirectResponse(url="/dashboard")
   ```

---

## 3. Strategia di Test & Validazione

1. **Test Automatico**:
   * Aggiungere un test `test_root_redirect` in `tests/controller/test_web_ui_views.py` che verifichi che effettuando una chiamata GET a `/` si riceva una risposta di redirect (status `307`) con l'header `Location` valorizzato a `/dashboard`.
   * Eseguire `docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py` per validare la rotta.
