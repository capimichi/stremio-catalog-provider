# Root Redirect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere un reindirizzamento da `/` a `/dashboard` per la Web UI.

**Architecture:** Registrazione di una rotta root `/` in `WebUiController` che restituisce un `RedirectResponse(url="/dashboard")`.

**Tech Stack:** FastAPI, Pytest

## Global Constraints

- Mantenere l'integrità dei commenti e dei docstring esistenti nel codice non modificato.
- Rispettare PEP 8 per tutte le modifiche Python.

---

### Task 1: Add Redirect Route & Verification Test

**Files:**
- Modify: `stremio_catalog_provider/controller/web_ui_controller.py`
- Modify: `tests/controller/test_web_ui_views.py`

**Interfaces:**
- Consumes: Niente
- Produces: Rotta root `/` funzionante con redirect e relativo test di regressione.

- [ ] **Step 1: Scrivere il test fallimentare in `test_web_ui_views.py`**

Modificare [test_web_ui_views.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/tests/controller/test_web_ui_views.py) aggiungendo il test in fondo al file:

```python
def test_root_path_redirects_to_dashboard() -> None:
    client = TestClient(app)
    # Eseguiamo una GET a / (non richiede auth perché il redirect avviene prima di chiedere auth sulla pagina di destinazione)
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "/dashboard"
```

- [ ] **Step 2: Eseguire pytest per verificare il fallimento**

Eseguire:
```bash
docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py::test_root_path_redirects_to_dashboard
```
Expected: FAIL con errore 404 (Not Found).

- [ ] **Step 3: Modificare `web_ui_controller.py`**

Modificare [web_ui_controller.py](file:///Users/michele/PycharmProjects/stremio-catalog-provider/stremio_catalog_provider/controller/web_ui_controller.py):
1. Righe 3-6, aggiungere l'import di `RedirectResponse`:
   ```python
   from fastapi.responses import HTMLResponse, RedirectResponse
   ```
2. In `_register_routes` (riga 60), aggiungere la rotta root:
   ```python
           self.router.add_api_route("/", self.root_redirect, methods=["GET"])
   ```
3. Aggiungere il metodo `root_redirect` in fondo alla classe `WebUiController`:
   ```python
       async def root_redirect(self) -> RedirectResponse:
           """Redirects root path to dashboard page."""
           return RedirectResponse(url="/dashboard")
   ```

- [ ] **Step 4: Eseguire pytest per verificare il superamento del test**

Eseguire:
```bash
docker compose run --rm web-api pytest tests/controller/test_web_ui_views.py::test_root_path_redirects_to_dashboard
```
Expected: PASS.

- [ ] **Step 5: Verificare l'intera suite di test**

Eseguire:
```bash
docker compose run --rm web-api pytest
```
Expected: PASS su tutti i 29 test.
