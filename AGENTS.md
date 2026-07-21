# Repository Guidelines

## Project Structure & Module Organization
- Source lives under `stremio_catalog_provider/`, split by responsibility: `controller/` (FastAPI routers), `service/` (business logic, entity-oriented where possible), `client/` (external integrations like TMDB and TorrServer), `entity/` (SQLAlchemy models), `repository/` (CRUD database operations), `container/` (dependency injection wiring), `command/` (Click CLI commands), `manager/` (global resource managers like database manager).
- Frontend assets live at the root of the project: `templates/` (Jinja2 HTML templates) and `static/` (CSS/JS files) to keep the Python namespace clean.
- Entry points: `stremio_catalog_provider/api.py` (FastAPI app) and `stremio_catalog_provider/cli.py` (CLI root). Extend new features by adding modules to the closest layer and binding them in the container.

## Development Setup & Commands
- Use the Docker container to run Python commands (e.g., CLI, tests, migrations) via `docker compose run --rm web-api <command>`.
  - For example, to run tests: `docker compose run --rm web-api pytest`
  - To run a CLI command: `docker compose run --rm web-api python -m stremio_catalog_provider.cli worker`
- Install deps with your preferred manager (e.g., `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`). Add to `requirements.txt` if you introduce dependencies.
- Run API locally: `uvicorn stremio_catalog_provider.api:app --reload --port 8000` or run the container system via `docker compose up`.
- Call the CLI example: `python -m stremio_catalog_provider.cli --help`.
- Format/import-sort before pushing.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep line length reasonable (≤100 chars).
- Use type hints throughout.
- Module/file names are `snake_case`; classes are `CapWords`; functions and variables are `snake_case`.
- Keep FastAPI routes thin: delegate to services; wire dependencies via the injector container.
- Always use Dependency Injection via `@inject` from `injector` for class dependencies. Place `@inject` on constructors so that services, controllers, etc., automatically resolve their dependencies without explicit configuration.
- In `DefaultContainer`, within the `_init_bindings` method, explicitly bind to `injector` only the classes that require a literal variable during initialization (e.g., environment configurations, API keys, URLs). If a class only requires other classes in its constructor, it will receive them implicitly from `injector`; do not explicitly bind them in `_init_bindings` to avoid redundant code.
- Never resolve dependencies or retrieve configuration values inside classes using `DefaultContainer.getInstance()`. Avoid the Service Locator pattern.
- Avoid defining constants at the module level (outside classes). Always define constants within the class scope where they are used to keep namespaces clean and improve modularity.
- Always keep import statements at the top of the file. Do not use inline/local imports.
- Never define loggers outside the class scope at the module level (e.g., `logger = logging.getLogger(__name__)`). Always inject a dedicated logger class or retrieve it via DI to keep the classes testable and modular.

## Testing Guidelines
- Use `pytest`. Place tests in `tests/` mirroring package structure (`tests/service/test_torrent_service.py`).
- Name tests with `test_` prefix; favor small, deterministic cases. Aim for meaningful coverage on services and controllers.
- Run tests: `pytest -q`.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise subject (`Add movie remapping service`), include focused changes only.
- PRs: describe behavior changes, add reproduction/testing notes, and link issues.

## Security & Configuration Tips
- Keep secrets out of the repo; load via environment variables. Never commit `.env`.
- When adding clients, isolate external calls in `client/` and mock them in tests.
