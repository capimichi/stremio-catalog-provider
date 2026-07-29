# Torrent Metadata and Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract additional torrent metadata (resolution, codec, quality, audio, and languages) using PTN/fallbacks, store it in the `torrents` table, and present it in Stremio stream results with a premium layout (name: `Catalog Provider {resolution}`, description formatted with emoji and details).

**Architecture:** 
- Configured languages are loaded from the environment variable `SUPPORTED_LANGUAGES` via `AppConfig`.
- `TorrentParserService` is updated using Dependency Injection to parse these fields and perform fallbacks (e.g. searching for common resolution substrings, checking for language keywords, mapping `"multi"` / `"dual"` to `"multi"`).
- `TorrentProcessService` stores these parsed parameters in `Torrent` during processing.
- `StremioService` formats stream objects using multi-line descriptions with emoji icons and language flag mapping.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PTN (parse-torrent-name).

## Global Constraints
- Keep lines in comments <= 100 chars.
- Follow PEP 8 with 4-space indentation.
- Always use Dependency Injection via `@inject` from `injector` for class dependencies.
- Never define constants at the module level.
- Keep import statements at the top of the file.

---

### Task 1: Database Migration and Model Update

**Files:**
- Modify: `stremio_catalog_provider/entity/torrent.py`
- Modify: `alembic/versions/1002_create_torrents.py`

**Interfaces:**
- Consumes: None
- Produces: New database columns (`resolution`, `codec`, `quality`, `audio`, `languages`) on `Torrent` entity.

- [ ] **Step 1: Update the Torrent model**
  Modify `stremio_catalog_provider/entity/torrent.py` to add the metadata fields.
  
  ```python
  # Add String to SQLAlchemy imports if not present
  from sqlalchemy import String
  
  # Inside class Torrent(BaseEntity):
  resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  audio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  languages: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
  ```

- [ ] **Step 2: Update the Alembic torrents table creation migration**
  Modify `alembic/versions/1002_create_torrents.py` to add columns to the create table statement so that fresh migrations are built correctly.
  
  ```python
  # Inside upgrade():
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
      sa.Column('media_id', sa.Integer(), nullable=True),
      sa.Column('resolution', sa.String(length=50), nullable=True),
      sa.Column('codec', sa.String(length=50), nullable=True),
      sa.Column('quality', sa.String(length=50), nullable=True),
      sa.Column('audio', sa.String(length=50), nullable=True),
      sa.Column('languages', sa.String(length=100), nullable=True),
      sa.ForeignKeyConstraint(['media_id'], ['media_items.id'], ),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('info_hash')
  )
  ```

- [ ] **Step 3: Run existing unit tests to check database model creation**
  Run: `PYTHONPATH=. pytest -v tests/entity/test_entities.py`
  Expected: PASS

---

### Task 2: AppConfig and Dependency Injection Wiring

**Files:**
- Modify: `stremio_catalog_provider/config/app_config.py`
- Modify: `stremio_catalog_provider/container/default_container.py`
- Modify: `stremio_catalog_provider/service/torrent_parser_service.py`

**Interfaces:**
- Consumes: `SUPPORTED_LANGUAGES` from environment variables.
- Produces: `AppConfig.supported_languages` property and injects `AppConfig` into `TorrentParserService`.

- [ ] **Step 1: Update AppConfig**
  Modify `stremio_catalog_provider/config/app_config.py` to parse and store the supported languages.
  
  ```python
  from typing import Optional, List
  
  class AppConfig:
      """Configuration for general application parameters."""
  
      def __init__(self, base_url: Optional[str] = None, supported_languages: Optional[str] = None) -> None:
          if base_url and not base_url.endswith("/"):
              base_url += "/"
          self.base_url = base_url
          # Parse comma-separated list of languages, lowercased and stripped
          self.supported_languages: List[str] = [
              lang.strip().lower() for lang in (supported_languages or "ita,eng").split(",") if lang.strip()
          ]
  ```

- [ ] **Step 2: Update DefaultContainer binding**
  Modify `stremio_catalog_provider/container/default_container.py` to pass the `SUPPORTED_LANGUAGES` environment variable to `AppConfig`.
  
  ```python
  # Inside _init_bindings(self):
  base_url = os.environ.get("BASE_URL")
  supported_langs = os.environ.get("SUPPORTED_LANGUAGES")
  
  self.injector.binder.bind(AppConfig, to=AppConfig(base_url, supported_langs))
  ```

- [ ] **Step 3: Update TorrentParserService constructor**
  Modify `stremio_catalog_provider/service/torrent_parser_service.py` to accept `AppConfig` via `@inject`.
  
  ```python
  from injector import inject
  from stremio_catalog_provider.config.app_config import AppConfig
  
  class TorrentParserService:
      """Service to parse media filenames using PTN (Python Torrent Name parser)."""
  
      @inject
      def __init__(self, app_config: AppConfig) -> None:
          self.app_config = app_config
  ```

- [ ] **Step 4: Verify container bindings**
  Run: `PYTHONPATH=. pytest -v tests/container/test_container.py`
  Expected: PASS

---

### Task 3: Torrent Parser Service Update (Metadata and Fallback Logic)

**Files:**
- Modify: `stremio_catalog_provider/service/torrent_parser_service.py`
- Modify: `tests/service/test_services.py`

**Interfaces:**
- Consumes: `parse_filename(self, filename: str)`
- Produces: Dictionary containing `title`, `season`, `episode`, `year`, `resolution`, `codec`, `quality`, `audio`, `languages`.

- [ ] **Step 1: Implement fallback and language logic in TorrentParserService**
  Modify `stremio_catalog_provider/service/torrent_parser_service.py`:
  
  ```python
  from typing import Any, Optional, List
  import PTN
  from injector import inject
  from stremio_catalog_provider.config.app_config import AppConfig
  
  class TorrentParserService:
      """Service to parse media filenames using PTN (Python Torrent Name parser)."""
  
      # Define language mapping and keywords in a class-level dictionary
      LANGUAGE_KEYWORDS = {
          "ita": ["ita", "italian", "italiano"],
          "eng": ["eng", "english", "inglese"],
          "deu": ["deu", "german", "deutsch"],
          "fra": ["fra", "french", "francais"],
          "spa": ["spa", "spanish", "espanol"]
      }
  
      @inject
      def __init__(self, app_config: AppConfig) -> None:
          self.app_config = app_config
  
      def parse_filename(self, filename: str) -> dict[str, Any]:
          """Parses a filename to extract title, season, episode, year, and metadata."""
          parsed = PTN.parse(filename)
          title = parsed.get("title")
          if not isinstance(title, str) or not title:
              title = filename
  
          # Standard season/episode parsing
          season: Optional[int] = None
          season_val = parsed.get("season")
          if isinstance(season_val, list) and len(season_val) > 0:
              season = int(season_val[0])
          elif isinstance(season_val, int):
              season = season_val
  
          episode: Optional[int] = None
          episode_val = parsed.get("episode")
          if isinstance(episode_val, list) and len(episode_val) > 0:
              episode = int(episode_val[0])
          elif isinstance(episode_val, int):
              episode = episode_val
  
          year: Optional[int] = None
          year_val = parsed.get("year")
          if isinstance(year_val, int):
              year = year_val
  
          # Extract technical metadata
          resolution = parsed.get("resolution")
          if isinstance(resolution, list) and len(resolution) > 0:
              resolution = str(resolution[0])
          elif resolution:
              resolution = str(resolution)
  
          codec = parsed.get("codec")
          if isinstance(codec, list) and len(codec) > 0:
              codec = str(codec[0])
          elif codec:
              codec = str(codec)
  
          quality = parsed.get("quality")
          if isinstance(quality, list) and len(quality) > 0:
              quality = str(quality[0])
          elif quality:
              quality = str(quality)
  
          audio = parsed.get("audio")
          if isinstance(audio, list) and len(audio) > 0:
              audio = str(audio[0])
          elif audio:
              audio = str(audio)
  
          # 1. Fallback for Resolution
          if not resolution:
              lower_fn = filename.lower()
              if "2160" in lower_fn or "4k" in lower_fn:
                  resolution = "2160p"
              elif "1080" in lower_fn:
                  resolution = "1080p"
              elif "720" in lower_fn:
                  resolution = "720p"
              elif "480" in lower_fn:
                  resolution = "480p"
              elif "360" in lower_fn:
                  resolution = "360p"
  
          # 2. Language Detection
          detected_langs: List[str] = []
          lower_fn = filename.lower()
  
          # Check for multi/dual
          if "multi" in lower_fn or "dual" in lower_fn:
              detected_langs.append("multi")
          else:
              # Check for configured languages
              for lang in self.app_config.supported_languages:
                  keywords = self.LANGUAGE_KEYWORDS.get(lang, [lang])
                  if any(kw in lower_fn for kw in keywords):
                      detected_langs.append(lang)
  
          languages_str: Optional[str] = ",".join(detected_langs) if detected_langs else None
  
          return {
              "title": title,
              "season": season,
              "episode": episode,
              "year": year,
              "resolution": resolution,
              "codec": codec,
              "quality": quality,
              "audio": audio,
              "languages": languages_str
          }
  ```

- [ ] **Step 2: Add test cases to verify parsing and fallback logic**
  Modify `tests/service/test_services.py` and replace `test_torrent_parser_service()`:
  
  ```python
  def test_torrent_parser_service() -> None:
      from stremio_catalog_provider.config.app_config import AppConfig
      config = AppConfig(supported_languages="ita,eng,deu")
      parser = TorrentParserService(config)
  
      # Standard PTN resolution extraction
      res1 = parser.parse_filename("The.Simpsons.S01E03.1080p.mkv")
      assert res1["title"] == "The Simpsons"
      assert res1["season"] == 1
      assert res1["episode"] == 3
      assert res1["resolution"] == "1080p"
  
      # Fallback resolution detection
      res2 = parser.parse_filename("MyMovie.1080.x264.mkv")
      assert res2["resolution"] == "1080p"
  
      # Configured language detection (Italian)
      res3 = parser.parse_filename("Dune.Parte.Due.2024.Italiano.H264.mkv")
      assert res3["languages"] == "ita"
  
      # Dual language detection
      res4 = parser.parse_filename("Dune.Parte.Due.2024.ita.eng.H264.mkv")
      assert "ita" in res4["languages"]
      assert "eng" in res4["languages"]
  
      # Multi/Dual fallback detection
      res5 = parser.parse_filename("Dune.Part.2.Dual.Audio.mkv")
      assert res5["languages"] == "multi"
  ```

- [ ] **Step 3: Run the updated test**
  Run: `PYTHONPATH=. pytest -v tests/service/test_services.py::test_torrent_parser_service`
  Expected: PASS

---

### Task 4: Torrent Process Service Integration

**Files:**
- Modify: `stremio_catalog_provider/service/torrent_process_service.py`
- Modify: `tests/service/test_torrent_process_service.py`

**Interfaces:**
- Consumes: `TorrentParserService.parse_filename`
- Produces: Saves all extracted properties on the `Torrent` entity.

- [ ] **Step 1: Save metadata to Torrent model during processing**
  Modify `stremio_catalog_provider/service/torrent_process_service.py` around line 69:
  
  ```python
  # Target content inside process_next_torrent:
  if first_video:
      parsed_file = self.parser_service.parse_filename(first_video)
      title = parsed_file.get("title")
      
      # Save metadata on torrent
      torrent.resolution = parsed_file.get("resolution")
      torrent.codec = parsed_file.get("codec")
      torrent.quality = parsed_file.get("quality")
      torrent.audio = parsed_file.get("audio")
      torrent.languages = parsed_file.get("languages")
  ```

- [ ] **Step 2: Update unit tests for TorrentProcessService**
  Modify `tests/service/test_torrent_process_service.py` to ensure the mock parser returns these fields, and assert they are saved in database.
  Look at the mocks in `test_process_next_torrent_with_predefined_media_item`. Ensure `parser_service.parse_filename` mock returns a dictionary with resolution, codec, quality, audio, and languages.
  Assert that the final torrent state in DB contains these fields.
  
  For example, in `test_process_next_torrent_with_predefined_media_item` and other tests in that file, ensure the parser service mock is set up like:
  ```python
  mock_parser.parse_filename.return_value = {
      "title": "Test Title",
      "season": 1,
      "episode": 2,
      "year": 2026,
      "resolution": "1080p",
      "codec": "H265",
      "quality": "WEBDL",
      "audio": "AC3",
      "languages": "ita,eng"
  }
  ```
  And assert:
  ```python
  assert db_torrent.resolution == "1080p"
  assert db_torrent.codec == "H265"
  assert db_torrent.quality == "WEBDL"
  assert db_torrent.audio == "AC3"
  assert db_torrent.languages == "ita,eng"
  ```

- [ ] **Step 3: Run the torrent process tests**
  Run: `PYTHONPATH=. pytest -v tests/service/test_torrent_process_service.py`
  Expected: PASS

---

### Task 5: Stremio Service Stream Formatting

**Files:**
- Modify: `stremio_catalog_provider/service/stremio_service.py`
- Modify: `tests/service/test_services.py`

**Interfaces:**
- Consumes: `StremioService.get_stream`
- Produces: List of streams with premium formatted `name` and `description`.

- [ ] **Step 1: Implement premium layout formatting in StremioService**
  Modify `stremio_catalog_provider/service/stremio_service.py`:
  Add a helper function to build the description:
  
  ```python
  # Inside StremioService class:
  
  # Emoji mapping dictionary
  LANGUAGE_EMOJIS = {
      "ita": "🇮🇹",
      "eng": "🇬🇧",
      "deu": "🇩🇪",
      "fra": "🇫🇷",
      "spa": "🇪🇸",
      "multi": "🌍",
      "dual": "🌍"
  }
  
  def _format_stream_description(self, mapping: FileMapping) -> str:
      torrent = mapping.torrent
      size_gb = mapping.file_size / (1024 * 1024 * 1024)
      
      # Technical details list
      tech_details = []
      if torrent.quality:
          tech_details.append(torrent.quality.upper())
      if torrent.codec:
          tech_details.append(torrent.codec.upper())
      if torrent.audio:
          tech_details.append(torrent.audio.upper())
          
      # Add flags
      if torrent.languages:
          langs = torrent.languages.split(",")
          flags = []
          for lang in langs:
              flags.append(self.LANGUAGE_EMOJIS.get(lang, "🌍"))
          tech_details.append(" ".join(flags))
          
      tech_str = " | ".join(tech_details)
      
      lines = [
          f"📄 {mapping.file_path}",
          f"💾 {size_gb:.2f} GB"
      ]
      if tech_str:
          lines.append(f"⚙️ {tech_str}")
          
      return "\n".join(lines)
  ```
  
  Now replace how the stream dictionaries are built inside `get_stream` (both for movies and series):
  
  ```python
  # For movies:
  streams.append({
      "name": f"Catalog Provider\n{m.torrent.resolution or ''}".strip(),
      "description": self._format_stream_description(m),
      "infoHash": m.torrent_hash,
      "fileIdx": m.file_index - 1,
      "sources": trackers
  })
  
  # For series:
  streams.append({
      "name": f"Catalog Provider\n{m.torrent.resolution or ''}".strip(),
      "description": self._format_stream_description(m),
      "infoHash": m.torrent_hash,
      "fileIdx": m.file_index - 1,
      "sources": trackers
  })
  ```

- [ ] **Step 2: Update tests in tests/service/test_services.py**
  Modify `test_stremio_service()` in `tests/service/test_services.py`:
  Make sure to set resolution, quality, codec, audio, and languages on the mock torrent object and assert the stream payload matches the new name and description keys.
  
  ```python
  # In test_stremio_service():
  torrent = Torrent(
      info_hash="hash123", 
      magnet_url="magnet123",
      resolution="1080p",
      quality="BluRay",
      codec="x265",
      audio="AC3",
      languages="ita,eng"
  )
  ```
  
  Change the stream assertions:
  ```python
  movie_stream = service.get_stream("movie", "ttMovie")
  assert len(movie_stream["streams"]) == 1
  stream = movie_stream["streams"][0]
  assert stream["name"] == "Catalog Provider\n1080p"
  assert "📄 movie.mkv" in stream["description"]
  assert "💾 1.00 GB" in stream["description"]
  assert "⚙️ BLURAY | X265 | AC3 | 🇮🇹 🇬🇧" in stream["description"]
  assert stream["infoHash"] == "hash123"
  assert stream["fileIdx"] == 0
  ```

- [ ] **Step 3: Run the stremio service test**
  Run: `PYTHONPATH=. pytest -v tests/service/test_services.py::test_stremio_service`
  Expected: PASS

- [ ] **Step 4: Run full test suite**
  Run: `PYTHONPATH=. pytest`
  Expected: PASS (All 32+ tests passing)
