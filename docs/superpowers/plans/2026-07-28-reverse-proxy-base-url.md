# Reverse Proxy & Gateway Streaming Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the `BASE_URL` configuration to support reverse proxies and implement a secure streaming proxy gateway in FastAPI to stream TorrServer video traffic to Stremio clients without exposing TorrServer.

**Architecture:** Create an `AppConfig` injected class to hold `BASE_URL` configured via environment variables. Modify stream link generation inside `StremioService` to point to a local proxy route `/stream/play/{torrent_hash}/{file_index}/{filename}`. Implement proxy routes in `StremioController` and the stream handler in `StremioService` that uses `httpx.AsyncClient` stream requests forwarding `Range` headers and propagating video stream response metadata (status, headers) and data chunks to the client.

**Tech Stack:** Python, FastAPI, httpx, pytest, injector

## Global Constraints

- Follow PEP 8 with 4-space indentation; keep line length <= 100 chars.
- Use type hints throughout.
- Always use Dependency Injection via `@inject` from `injector` for class dependencies.
- Keep FastAPI routes thin: delegate logic to services.
- Never resolve dependencies using `DefaultContainer.getInstance()`.
- Avoid defining constants outside classes (keep them in class scope).
- Keep imports at the top of the file; do not use inline/local imports.

---

### Task 1: AppConfig & DefaultContainer Configuration

**Files:**
- Create: `stremio_catalog_provider/config/app_config.py`
- Modify: `stremio_catalog_provider/container/default_container.py`
- Modify: `.env.example`
- Create: `tests/config/test_app_config.py`

**Interfaces:**
- Produces: `AppConfig` class with `base_url: Optional[str]` property.

- [ ] **Step 1: Write the config tests**
  Create `tests/config/test_app_config.py` containing tests for configuration instantiation and trailing slash normalization:
  ```python
  from stremio_catalog_provider.config.app_config import AppConfig

  def test_app_config_normalizes_base_url():
      # Test url without trailing slash
      config = AppConfig(base_url="https://example.com")
      assert config.base_url == "https://example.com/"

      # Test url with trailing slash
      config = AppConfig(base_url="https://example.com/")
      assert config.base_url == "https://example.com/"

      # Test empty url
      config = AppConfig(base_url=None)
      assert config.base_url is None
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/config/test_app_config.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'stremio_catalog_provider.config.app_config'`

- [ ] **Step 3: Implement AppConfig**
  Create `stremio_catalog_provider/config/app_config.py`:
  ```python
  from typing import Optional

  class AppConfig:
      """Configuration for general application parameters."""

      def __init__(self, base_url: Optional[str] = None) -> None:
          if base_url and not base_url.endswith("/"):
              base_url += "/"
          self.base_url = base_url
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/config/test_app_config.py -v`
  Expected: PASS

- [ ] **Step 5: Write the DefaultContainer test**
  Modify/create a container test to assert `AppConfig` is bound in the injector container. Create `tests/container/test_default_container_app_config.py`:
  ```python
  from stremio_catalog_provider.container.default_container import DefaultContainer
  from stremio_catalog_provider.config.app_config import AppConfig

  def test_container_binds_app_config():
      container = DefaultContainer.getInstance()
      app_config = container.get(AppConfig)
      assert isinstance(app_config, AppConfig)
  ```

- [ ] **Step 6: Run test to verify it fails**
  Run: `pytest tests/container/test_default_container_app_config.py -v`
  Expected: FAIL with `UnboundTypeError: Could not find tile/class for <class 'stremio_catalog_provider.config.app_config.AppConfig'>`

- [ ] **Step 7: Bind AppConfig in DefaultContainer**
  Modify `stremio_catalog_provider/container/default_container.py`:
  ```python
  # Add imports at the top
  from stremio_catalog_provider.config.app_config import AppConfig

  # In _init_bindings:
  base_url = os.environ.get("BASE_URL")
  self.injector.binder.bind(AppConfig, to=AppConfig(base_url))
  ```

- [ ] **Step 8: Run test to verify it passes**
  Run: `pytest tests/container/test_default_container_app_config.py -v`
  Expected: PASS

- [ ] **Step 9: Update `.env.example`**
  Modify `.env.example` to document the new `BASE_URL` environment variable:
  ```ini
  # URL pubblico di questo provider per la dashboard e lo streaming (opzionale)
  # Se vuoto, verrà utilizzato l'indirizzo della richiesta HTTP (request.base_url)
  BASE_URL=
  ```

---

### Task 2: Controller Dependency Injection & Dashboard Updates

**Files:**
- Modify: `stremio_catalog_provider/controller/web_ui_controller.py`
- Modify: `stremio_catalog_provider/controller/stremio_controller.py`
- Modify: `tests/controller/test_web_ui_controller.py`

**Interfaces:**
- Consumes: `AppConfig` from Task 1

- [ ] **Step 1: Write test for WebUiController dashboard with BASE_URL**
  Modify `tests/controller/test_web_ui_controller.py` (or create it if needed) to ensure that the dashboard route uses the configured `BASE_URL` over the request base URL.
  ```python
  from unittest.mock import MagicMock
  from fastapi import Request
  from stremio_catalog_provider.controller.web_ui_controller import WebUiController
  from stremio_catalog_provider.config.app_config import AppConfig

  def test_dashboard_uses_configured_base_url():
      # Mock dependencies
      torrent_repo = MagicMock()
      torrent_repo.get_all.return_value = []
      media_repo = MagicMock()
      media_repo.search_local.return_value = []
      templates = MagicMock()
      app_config = AppConfig(base_url="https://public-host.com")
      
      controller = WebUiController(
          torrent_repo=torrent_repo,
          media_repo=media_repo,
          templates=templates,
          app_config=app_config
      )
      
      request = MagicMock(spec=Request)
      request.base_url = "http://localhost:8000"
      
      credentials = MagicMock()
      controller.verify_credentials = MagicMock()
      
      controller.dashboard(request=request, credentials=credentials)
      
      # Verify that templates.TemplateResponse was called with public base_url
      args, kwargs = templates.TemplateResponse.call_args
      context = args[2]
      assert context["stremio_url"] == "https://public-host.com/manifest.json"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/controller/test_web_ui_controller.py -v`
  Expected: FAIL (missing `app_config` parameter or assertion failure on `stremio_url`)

- [ ] **Step 3: Update WebUiController**
  Modify `stremio_catalog_provider/controller/web_ui_controller.py`:
  1. Add import: `from stremio_catalog_provider.config.app_config import AppConfig`
  2. Inject `app_config: AppConfig` into `__init__`.
  3. Modify the `dashboard` method to compute `stremio_url` using the base URL from `AppConfig` if present, falling back to `request.base_url`:
  ```python
      # In __init__:
      self.app_config = app_config

      # In dashboard:
      base_url = self.app_config.base_url or str(request.base_url)
      if not base_url.endswith("/"):
          base_url += "/"
      stremio_url = f"{base_url}manifest.json"
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/controller/test_web_ui_controller.py -v`
  Expected: PASS

- [ ] **Step 5: Update StremioController dependency injection**
  Modify `stremio_catalog_provider/controller/stremio_controller.py`:
  1. Add import: `from fastapi import Request`
  2. Modify the `/stream/{media_type}/{stream_id}.json` route to accept `request: Request`.
  3. Pass `request` down to `self.stremio_service.get_stream`.
  ```python
      # In _register_routes:
      self.router.add_api_route(
          "/stream/{media_type}/{stream_id}.json", self.stream, methods=["GET"]
      )

      # In stream method signature:
      async def stream(self, media_type: str, stream_id: str, request: Request) -> dict[str, Any]:
          return self.stremio_service.get_stream(media_type, stream_id, request)
  ```

---

### Task 3: StremioService Stream Link Generation Update

**Files:**
- Modify: `stremio_catalog_provider/service/stremio_service.py`
- Modify: `tests/service/test_stremio_service.py`

**Interfaces:**
- Consumes: `AppConfig` from Task 1
- Produces: `get_stream(media_type, stream_id, request=None)` returning proxy streaming links instead of direct TorrServer links.

- [ ] **Step 1: Write test for get_stream proxy link generation**
  Modify `tests/service/test_stremio_service.py` to assert that streams returned point to the new `/stream/play/{hash}/{index}/{filename}` URL.
  ```python
  from unittest.mock import MagicMock
  from fastapi import Request
  from stremio_catalog_provider.service.stremio_service import StremioService
  from stremio_catalog_provider.config.app_config import AppConfig
  from stremio_catalog_provider.config.torrserver_config import TorrServerConfig
  from stremio_catalog_provider.entity.file_mapping import FileMapping

  def test_get_stream_returns_proxy_urls():
      # Mock dependencies
      media_repo = MagicMock()
      mapping_repo = MagicMock()
      torr_config = TorrServerConfig("http://local-torr:8090")
      app_config = AppConfig("https://public-site.com")
      
      session = MagicMock()
      mapping_repo.get_session.return_value = session
      
      # Mock movie item
      mock_media = MagicMock()
      mock_media.id = 1
      media_repo.get_by_imdb_id.return_value = mock_media
      
      # Mock FileMapping
      mock_mapping = FileMapping()
      mock_mapping.torrent_id = 1
      mock_mapping.file_index = 0
      mock_mapping.file_path = "movies/Terminator.mp4"
      mock_mapping.file_size = 104857600
      # Mock torrent relation/property
      mock_torrent = MagicMock()
      mock_torrent.info_hash = "abcdef1234567890"
      mock_mapping.torrent = mock_torrent
      
      session.query.return_value.filter_by.return_value.all.return_value = [mock_mapping]
      
      service = StremioService(media_repo, mapping_repo, torr_config, app_config)
      
      request = MagicMock(spec=Request)
      result = service.get_stream("movie", "tt0084756", request)
      
      streams = result.get("streams", [])
      assert len(streams) == 1
      # Must point to the proxy endpoint, ending with the URL-quoted filename
      assert streams[0]["url"] == "https://public-site.com/stream/play/abcdef1234567890/0/Terminator.mp4"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/service/test_stremio_service.py -v`
  Expected: FAIL (assertion error: stream URL points to TorrServer local address instead of proxy URL)

- [ ] **Step 3: Update StremioService constructor and get_stream**
  Modify `stremio_catalog_provider/service/stremio_service.py`:
  1. Add import: `import urllib.parse`
  2. Add import: `from fastapi import Request`
  3. Add import: `from stremio_catalog_provider.config.app_config import AppConfig`
  4. Inject `app_config: AppConfig` into `__init__` and store as `self.app_config`.
  5. Update `get_stream` method signature and internal URL construction:
  ```python
      # In __init__:
      self.app_config = app_config

      # In get_stream signature:
      def get_stream(self, media_type: str, stream_id: str, request: Optional[Request] = None) -> dict[str, Any]:
          # ...
          provider_base_url = self.app_config.base_url
          if not provider_base_url and request:
              provider_base_url = str(request.base_url)
          if not provider_base_url:
              provider_base_url = "http://localhost:8000/"

          # Inside movie mappings loop:
          filename = m.file_path.split("/")[-1]
          encoded_filename = urllib.parse.quote(filename)
          stream_url = f"{provider_base_url}stream/play/{m.torrent_hash}/{m.file_index}/{encoded_filename}"

          # Inside series mappings loop:
          filename = m.file_path.split("/")[-1]
          encoded_filename = urllib.parse.quote(filename)
          stream_url = f"{provider_base_url}stream/play/{m.torrent_hash}/{m.file_index}/{encoded_filename}"
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/service/test_stremio_service.py -v`
  Expected: PASS

---

### Task 4: Gateway Streaming Proxy Route & Logic

**Files:**
- Modify: `stremio_catalog_provider/service/stremio_service.py`
- Modify: `stremio_catalog_provider/controller/stremio_controller.py`
- Create: `tests/controller/test_stremio_streaming_proxy.py`

**Interfaces:**
- Produces: `get_stream_proxy(torrent_hash, file_index, range_header)` method in `StremioService` returning `(generator, status_code, headers)`.
- Produces: `play_stream` endpoint in `StremioController` mounted on `/stream/play/{torrent_hash}/{file_index}` and `/stream/play/{torrent_hash}/{file_index}/{filename}`.

- [ ] **Step 1: Write tests for the streaming proxy gateway**
  Create `tests/controller/test_stremio_streaming_proxy.py`. This tests that the FastAPI route correctly forwards requests to TorrServer, forwards range headers, and handles HTTP response chunks properly.
  ```python
  import httpx
  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch
  from fastapi import FastAPI
  from fastapi.testclient import TestClient
  from stremio_catalog_provider.controller.stremio_controller import StremioController
  from stremio_catalog_provider.service.stremio_service import StremioService

  @pytest.mark.asyncio
  async def test_play_stream_proxying_flow():
      stremio_service = MagicMock(spec=StremioService)
      
      # Mock the generator and return values
      async def mock_generator():
          yield b"video_chunk_1"
          yield b"video_chunk_2"
          
      stremio_service.get_stream_proxy = AsyncMock(return_value=(
          mock_generator(),
          206,
          {"content-range": "bytes 0-10/20", "content-length": "13", "content-type": "video/mp4"}
      ))
      
      # Setup FastAPI app for testing
      app = FastAPI()
      controller = StremioController(stremio_service)
      app.include_router(controller.router)
      
      client = TestClient(app)
      
      # Request stream play
      response = client.get("/stream/play/hash123/2", headers={"Range": "bytes=0-"})
      
      # Assertions
      assert response.status_code == 206
      assert response.headers["content-range"] == "bytes 0-10/20"
      assert response.headers["content-length"] == "13"
      assert response.headers["content-type"] == "video/mp4"
      assert response.content == b"video_chunk_1video_chunk_2"
      
      stremio_service.get_stream_proxy.assert_called_once_with("hash123", 2, "bytes=0-")
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/controller/test_stremio_streaming_proxy.py -v`
  Expected: FAIL with `AttributeError` (missing method `get_stream_proxy` or routing endpoints)

- [ ] **Step 3: Implement get_stream_proxy in StremioService**
  Modify `stremio_catalog_provider/service/stremio_service.py` to add `get_stream_proxy`. It uses `httpx.AsyncClient` with a context manager streaming response, handles Basic Auth headers from `TorrServerConfig`, and yields bytes chunks while cleaning up resources on completion/disconnection.
  ```python
      # Add to StremioService class:
      async def get_stream_proxy(
          self, torrent_hash: str, file_index: int, range_header: Optional[str]
      ) -> Tuple[AsyncGenerator[bytes, None], int, Dict[str, str]]:
          """Proxies the stream request directly to TorrServer, preserving range headers."""
          headers = {}
          if range_header:
              headers["Range"] = range_header

          auth = None
          if self.torr_config.username and self.torr_config.password:
              auth = (self.torr_config.username, self.torr_config.password)

          url = f"{self.torr_config.base_url}/stream"
          params = {"link": str(file_index), "hash": torrent_hash, "play": ""}

          client = httpx.AsyncClient()
          try:
              req = client.build_request("GET", url, params=params, headers=headers, auth=auth)
              response = await client.send(req, stream=True, timeout=None)
              
              propagate_headers = {}
              for h in ["content-range", "content-length", "content-type", "accept-ranges"]:
                  if h in response.headers:
                      propagate_headers[h] = response.headers[h]

              async def chunk_generator() -> AsyncGenerator[bytes, None]:
                  try:
                      async for chunk in response.aiter_bytes(chunk_size=128 * 1024):
                          yield chunk
                  finally:
                      await response.aclose()
                      await client.aclose()

              return chunk_generator(), response.status_code, propagate_headers

          except Exception as e:
              await client.aclose()
              raise e
  ```

- [ ] **Step 4: Add play_stream endpoint in StremioController**
  Modify `stremio_catalog_provider/controller/stremio_controller.py`:
  1. Update `_register_routes` to mount the proxy routes:
  ```python
      # In _register_routes:
      self.router.add_api_route(
          "/stream/play/{torrent_hash}/{file_index}", self.play_stream, methods=["GET"]
      )
      self.router.add_api_route(
          "/stream/play/{torrent_hash}/{file_index}/{filename}", self.play_stream, methods=["GET"]
      )
  ```
  2. Implement `play_stream` method:
  ```python
      async def play_stream(
          self, torrent_hash: str, file_index: int, request: Request, filename: str = ""
      ) -> StreamingResponse:
          """Proxies the media stream request from TorrServer using range headers."""
          range_header = request.headers.get("range")
          generator, status_code, headers = await self.stremio_service.get_stream_proxy(
              torrent_hash, file_index, range_header
          )
          return StreamingResponse(generator, status_code=status_code, headers=headers)
  ```

- [ ] **Step 5: Run tests to verify they pass**
  Run: `pytest tests/controller/test_stremio_streaming_proxy.py -v`
  Expected: PASS

- [ ] **Step 6: Run full test suite**
  Run: `pytest`
  Expected: All tests pass, ensuring no regression.
