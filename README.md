# replay-llm-call

A clean and practical AI Agent project built with Pydantic-AI + FastAPI. Ready-to-use configuration, structured logging, error handling, and Docker support for quickly building production-ready Agent services or CLI tools.

> 📖 **中文文档**: [README_zh.md](README_zh.md)

## Prerequisites (Environment Setup)
- Operating System: macOS / Linux / Windows (with make installed)
- Python: 3.11 (required - this project uses a fixed Python version)
- **Package Manager: uv (required)** - This project is built with uv for fast dependency management
- Optional Dependencies: Docker, PostgreSQL, Redis

### Install uv (Required)
This project uses uv as the package manager. Install it first:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative: via pip
pip install uv
```

## Quick Start
1) Clone the repository and enter the directory
```bash
git clone <your-repo-url>
cd replay_llm_call
```

2) Complete project setup (installs dependencies, creates .env, directories, and test skeleton)
```bash
make setup
```

3) Start running
- CLI mode:
```bash
make run-cli
```
- API mode:
```bash
make run-api
```
In API mode, the service runs on `http://localhost:8080` by default, with interactive documentation at `/docs`.

> For development with hot reload: `make run-api-dev`

## Configuration
- Copy `env.sample` to `.env` and fill in API keys, database, cache, and other configurations as needed.
- Validate configuration:
```bash
make config-check
```

## Common Commands (via Makefile)
- View all commands and categorized help: `make help`
- Setup: `make setup` (installs dependencies with uv, creates .env, directories)
- Run CLI: `make run-cli`
- Run API: `make run-api` (or hot reload `make run-api-dev`)
- Run tests: `make test` (or verbose mode `make test-verbose`)
- Code quality: `make format`, `make lint`, `make type-check`
- Docker: `make docker-build`, `make docker-run`
- Others: `make clean`, `make clean-logs`, `make version`

> **Note**: All Python commands automatically use `uv run` when uv is available, ensuring consistent dependency management.

## Project Structure

```
replay_llm_call/
├── src/                     # Main source code directory
│   ├── core/                # Core modules (config, logging, etc.)
│   ├── agents/              # AI Agent implementations
│   ├── api/                 # FastAPI routes and endpoints
│   ├── models/              # Data models
│   └── utils/               # Utility functions
├── tests/                   # Test files
├── docs/                    # Project documentation
├── logs/                    # Log files directory
├── main.py                  # Application entry point
├── pyproject.toml           # Project configuration and dependencies
├── uv.lock                  # uv lock file
├── env.sample               # Environment variables template
└── Makefile                 # Development commands
```

## Documentation
- Architecture & Conventions: `docs/ARCHITECTURE.md`
- See `docs/` directory for more documentation (can be supplemented with project-specific guides)

## Docker Quick Usage (Optional)
```bash
make docker-build
make docker-run
```

## Contributing & License
- Welcome to submit Issues / PRs to improve the template together
- License: MIT (see LICENSE file in repository)