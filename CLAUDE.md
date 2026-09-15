# Repository Guidelines

## Commands
- Dev: `python -m daily_brief.main`
- Build: `pip install -e .`
- Test: `pytest`
- Lint: `ruff check . && ruff format .`
- Typecheck: `mypy .`

## Architecture & Entrypoints
- Entrypoint: `src/daily_brief/main.py`
- API Handlers: `src/daily_brief/canvas/` and `src/daily_brief/coursemology/`
- Persistence: `src/daily_brief/services/` (FileStorage)
- Routing: CLI application orchestrated in `src/daily_brief/main.py`

## Invariants & Rules
- Imports: Absolute imports from the `daily_brief` package.
- Configuration: `python-dotenv` loading from `.env` file, keys defined in `.env.example`, accessed via `get_env_var`.
- Typings: Strict type hinting with Python 3.10+ type annotations (e.g. `tuple[list[str], list[str]]`).
- Test Convention: `pytest` runner, files matching `test_*.py` located in the `tests/` directory.
