# Design Spec: Torrent Metadata Extraction and Stream Formatting

This specification defines the design to extract more metadata from torrent filenames (resolution, codec, quality, audio, and languages), store it in the database, and display it in Stremio streams using a premium, multi-line format.

## 1. Goal & Requirements
- Extract `resolution`, `codec`, `quality`, `audio` using PTN from media filenames.
- **Fallback**: If PTN fails to identify the resolution, check case-insensitively for common resolutions (`2160`, `1080`, `720`, `480`, `360`) in the filename.
- **Configurable Languages**: Detect languages configured via `SUPPORTED_LANGUAGES` env variable (e.g. `ita,eng`). If `multi` or `dual` is found in the filename, treat it as a distinct value (`multi`).
- **Database Storage**: Store these properties in the `torrents` table.
- **Premium Stremio Streams**: Present streams to Stremio with:
  - `name`: `Catalog Provider {resolution}` (e.g., `Catalog Provider 1080p`)
  - `description` formatted on multiple lines:
    ```text
    📄 {filename}
    💾 {size} GB
    ⚙️ {quality} | {codec} | {audio} | {language_emojis}
    ```
    - Language mapping: `ita` -> `🇮🇹`, `eng` -> `🇬🇧`, `multi` -> `🌍`, `dual` -> `🌍`, others -> their respective flags (or `🌍` as fallback).

---

## 2. Configuration & Dependency Injection
An env variable `SUPPORTED_LANGUAGES` will be introduced (defaulting to `"ita,eng"`).
- **`AppConfig`**: Will be extended to load `supported_languages` as a list of cleaned strings:
  ```python
  self.supported_languages = [lang.strip().lower() for lang in (supported_languages or "ita,eng").split(",")]
  ```
- **`DefaultContainer`**: Will pass `os.environ.get("SUPPORTED_LANGUAGES")` to `AppConfig`.
- **`TorrentParserService`**: Will receive `AppConfig` via `@inject` constructor injection to know which languages to detect.

---

## 3. Database Changes
Modify the `torrents` table by updating the SQLAlchemy model and the original Alembic migration:
- **Model** (`stremio_catalog_provider/entity/torrent.py`):
  ```python
  resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  audio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  languages: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Comma-separated
  ```
- **Migration** (`alembic/versions/1002_create_torrents.py`):
  Add corresponding columns to `op.create_table('torrents', ...)` to keep creation migrations fully aligned.

---

## 4. Parser Service & Fallbacks
Update `TorrentParserService.parse_filename`:
1. Parse filename with `PTN`.
2. Extract `resolution`, `codec`, `quality`, `audio` keys.
3. **Resolution Fallback**: If not found in PTN results, search filename case-insensitively for:
   - `"2160"` or `"4k"` -> `"2160p"`
   - `"1080"` -> `"1080p"`
   - `"720"` -> `"720p"`
   - `"480"` -> `"480p"`
   - `"360"` -> `"360p"`
4. **Language Detection**:
   - Check case-insensitively for `"multi"` or `"dual"` in filename -> add `"multi"`.
   - Check case-insensitively for configured language strings in the filename (e.g. for `ita`: check `"ita"`, `"italian"`, `"italiano"`; for `eng`: check `"eng"`, `"english"`, `"inglese"`).
   - Combine detected languages into a comma-separated string (e.g. `"ita,eng"` or `"multi"`).

---

## 5. Torrent Process Service
In `TorrentProcessService.process_next_torrent`:
When the first video file is found and parsed, we update the torrent entity:
```python
parsed_file = self.parser_service.parse_filename(first_video)
torrent.title = parsed_file.get("title")
torrent.resolution = parsed_file.get("resolution")
torrent.codec = parsed_file.get("codec")
torrent.quality = parsed_file.get("quality")
torrent.audio = parsed_file.get("audio")
torrent.languages = parsed_file.get("languages")
```

---

## 6. Stremio Addon Streams API
Update `StremioService.get_stream`:
Format each stream returned:
- `name`: `f"Catalog Provider {m.torrent.resolution or ''}".strip()`
- `description`:
  ```text
  📄 {m.file_path}
  💾 {size_gb:.2f} GB
  ⚙️ {technical_details}
  ```
  Where `technical_details` is a string constructed of:
  `{quality} | {codec} | {audio} | {language_emojis}` (only including non-empty fields).
  Language emoji helper:
  - `ita` -> `🇮🇹`
  - `eng` -> `🇬🇧`
  - `deu` -> `🇩🇪`
  - `fra` -> `🇫🇷`
  - `spa` -> `🇪🇸`
  - `multi`, `dual`, others -> `🌍`

---

## 7. Testing Strategy
- Add unit tests in `tests/service/test_services.py` for language detection, resolution fallback, and formatting.
- Ensure existing integration tests continue to pass.
