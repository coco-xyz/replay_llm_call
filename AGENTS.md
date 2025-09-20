# Repository Guidelines

## Project Structure & Module Organization
- `src/core` contains configuration, logging, and LLM integration primitives; treat it as shared infrastructure.
- `src/agents` holds agent orchestrators, with prompt templates alongside in `src/prompts`.
- `src/api` exposes FastAPI routers; `src/services` coordinate business flows and `src/stores` wrap persistence layers.
- Templates live in `templates/`, front-end assets in `static/`, migrations in `migrations/`, and canonical tests in `tests/`. Use `docs/` for design notes and `main.py` plus the `Makefile` as entry points.

## Build, Test, and Development Commands
- `make setup` installs dependencies via uv, creates `.env`, and prepares log/test directories.
- `make run-cli` executes the agent CLI; `make run-api` (or `make run-api-dev`) runs the FastAPI service on `http://localhost:8080` with optional reload.
- `make test` runs pytest with async support; `make test-verbose` adds detailed traces for debugging.
- `make format`, `make lint`, and `make type-check` invoke Black, Flake8, and Mypy—expect clean runs before pushing.
- Docker workflows use `make docker-build` and `make docker-run` to mirror production containers locally.

## Coding Style & Naming Conventions
- Target Python 3.11; keep modules and files snake_case, classes PascalCase, and constants UPPER_SNAKE.
- Black enforces 88-character lines and isort uses the `black` profile. Run `make format` after substantial edits to sync both.
- Maintain type hints; Mypy runs with strict flags, so declare return types and avoid implicit `Optional` values.
- Prefer structured logging through `src/core/logger.py` and reusable service layers over inline business logic.

## Testing Guidelines
- Co-locate pytest suites under `tests/` mirroring the source layout; filenames follow `test_*.py` and async cases use `pytest.mark.asyncio`.
- Tag slow or external-resource checks with `@pytest.mark.integration` so they can be excluded via `-m "not integration"`.
- Every feature should ship with happy-path and edge-case coverage; keep fixtures minimal and reuse helpers from `tests/conftest.py`.

## Commit & Pull Request Guidelines
- Commit summaries stay in the imperative mood (see recent `git log`); keep the first line ≤72 characters and add context in a wrapped body when needed.
- Group changes by concern and run `make test` plus quality targets before pushing to avoid CI churn.
- Pull requests must explain intent, link related issues, list the verification commands, and attach UI screenshots for changes under `templates/` or `static/`.
- Highlight configuration updates (`.env`, `env.sample`, or infrastructure manifests) and request reviewers familiar with cross-agent impacts.
