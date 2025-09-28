# Repository Guidelines

## Project Structure & Module Organization
- `src/core` hosts shared configuration, logging utilities, and LLM adapters—treat these as single sources of truth.
- `src/agents` defines orchestrators, with supporting prompt templates under `src/prompts` and coordination helpers in `src/services`.
- API entry points live in `src/api`, while persistence wrappers stay in `src/stores`; UI templates sit in `templates/` with assets in `static/`.
- Tests mirror the source tree under `tests/`; refer to `docs/` for design notes, `main.py` for runtime bootstrap, and the `Makefile` for day-to-day automation.

## Build, Test, and Development Commands
- `make setup` provisions the environment (uv install, `.env`, log/test dirs).
- `make run-cli` launches the interactive agent CLI for manual workflows.
- `make run-api` or `make run-api-dev` serves the FastAPI app on `http://localhost:8080` (reload enabled in `-dev`).
- `make test` runs pytest with async fixtures; append `-verbose` for trace-heavy debugging.
- `make format`, `make lint`, and `make type-check` run Black/isort, Flake8, and Mypy; expect clean passes before merging.
- Container parity commands: `make docker-build` and `make docker-run`.

## Coding Style & Naming Conventions
- Target Python 3.11 with Black's 88-character lines and isort `black` profile (run `make format` after edits).
- Modules and files use `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`; keep agent prompt IDs descriptive but concise.
- Uphold strict typing—avoid implicit `Optional` and prefer structured logging via `src/core/logger.py`.

## Testing Guidelines
- Name suites `tests/<module>/test_*.py`; async tests require `@pytest.mark.asyncio`.
- Tag external or long-running scenarios with `@pytest.mark.integration` so `pytest -m "not integration"` stays fast.
- Cover happy paths, error handling, and store/service boundaries, reusing fixtures from `tests/conftest.py` to limit setup drift.

## Commit & Pull Request Guidelines
- Write imperative, ≤72 character commit titles and group related edits; mention follow-up context in the body when needed.
- Before pushing, run `make test`, `make lint`, `make type-check`, and `make format` to keep CI green.
- PRs must state intent, link issues, enumerate verification commands, and attach screenshots for `templates/` or `static/` updates.
- Call out configuration changes (`.env`, `env.sample`, docker manifests) and request reviewers aware of cross-agent impact.

## Security & Configuration Tips
- Never commit secrets; derive local settings from `env.sample` via `make setup` and document additions there.
- Rotate API keys through environment variables and prefer `src/core` helpers for credential access.
- When adding dependencies, update `pyproject.toml` and regenerate `uv.lock` using `uv pip compile` to maintain reproducibility.
