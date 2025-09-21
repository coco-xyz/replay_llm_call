# replay-llm-call - Makefile
# Essential development commands for AI agent application

# =============================================================================
# Configuration
# =============================================================================

# Project settings
PROJECT_NAME := replay-llm-call
PACKAGE_NAME := replay_llm_call

# Docker settings
DOCKER_IMAGE := $(PROJECT_NAME)
DOCKER_TAG := latest

# Docker Compose command - check if docker compose (v2) is available, fallback to docker-compose (v1)
DOCKER_COMPOSE := $(shell command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

# Environment settings
ENV_FILE := .env
ENV_SAMPLE := env.sample

# Directories
SRC_DIR := src
TESTS_DIR := tests
LOGS_DIR := logs

# Python command - check if uv is available, fallback to python
PYTHON_CMD := $(shell command -v uv >/dev/null 2>&1 && echo "uv run python" || echo "python")

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
RESET := \033[0m

# =============================================================================
# Help and Default Target
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)replay-llm-call - Development Commands$(RESET)"
	@echo "$(CYAN)================================================$(RESET)"
	@echo ""
	@echo "$(YELLOW)Setup Commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*setup/ {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Development Commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*dev/ {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Testing Commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*test/ {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Code Quality Commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*quality/ {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Docker Commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## .*docker/ {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Utility Commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / && !/setup|dev|test|quality|docker/ {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help

# =============================================================================
# Setup Commands
# =============================================================================

.PHONY: setup-deps
setup-deps: ## setup - Install dependencies with uv
	@echo "$(BLUE)Installing dependencies with uv...$(RESET)"
	@if command -v uv >/dev/null 2>&1; then \
		uv sync; \
		echo "$(GREEN)✅ Dependencies installed$(RESET)"; \
	else \
		echo "$(RED)❌ uv not found$(RESET)"; \
		echo "$(YELLOW)Please install uv first: https://docs.astral.sh/uv/getting-started/installation/$(RESET)"; \
		exit 1; \
	fi

.PHONY: setup-env
setup-env: ## setup - Create .env file from template
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(BLUE)Creating .env file from template...$(RESET)"; \
		cp $(ENV_SAMPLE) $(ENV_FILE); \
		echo "$(GREEN)✅ Created .env file$(RESET)"; \
		echo "$(YELLOW)⚠️  Please edit .env file with your configuration$(RESET)"; \
	else \
		echo "$(YELLOW).env file already exists$(RESET)"; \
	fi

.PHONY: setup-dirs
setup-dirs: ## setup - Create necessary directories
	@echo "$(BLUE)Creating project directories...$(RESET)"
	@mkdir -p $(LOGS_DIR) $(TESTS_DIR)
	@echo "$(GREEN)✅ Directories created$(RESET)"

# =============================================================================
# Development Commands
# =============================================================================

.PHONY: run-cli
run-cli: ## dev - Run application in CLI mode
	@echo "$(BLUE)Starting CLI mode...$(RESET)"
	$(PYTHON_CMD) main.py --mode cli

.PHONY: run-api
run-api: ## dev - Run application in API mode
	@echo "$(BLUE)Starting API server...$(RESET)"
	$(PYTHON_CMD) main.py --mode api

.PHONY: run-api-dev
run-api-dev: ## dev - Run API server with auto-reload
	@echo "$(BLUE)Starting API server with auto-reload...$(RESET)"
	$(PYTHON_CMD) main.py --mode api --reload

.PHONY: shell
shell: ## dev - Start interactive Python shell with project context
	@echo "$(BLUE)Starting Python shell...$(RESET)"
	$(PYTHON_CMD) -i -c "from src.core.config import settings; print('Settings loaded:', settings is not None)"

# =============================================================================
# Testing Commands
# =============================================================================

.PHONY: test
test: ## test - Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	$(PYTHON_CMD) -m pytest

.PHONY: test-verbose
test-verbose: ## test - Run tests with verbose output
	@echo "$(BLUE)Running tests with verbose output...$(RESET)"
	$(PYTHON_CMD) -m pytest -v

.PHONY: test-create
test-create: ## test - Create basic test structure
	@echo "$(BLUE)Creating test structure...$(RESET)"
	@mkdir -p $(TESTS_DIR)
	@if [ ! -f $(TESTS_DIR)/__init__.py ]; then touch $(TESTS_DIR)/__init__.py; fi
	@if [ ! -f $(TESTS_DIR)/conftest.py ]; then \
		echo "import pytest\nfrom src.core.config import settings\n\n@pytest.fixture\ndef test_settings():\n    return settings" > $(TESTS_DIR)/conftest.py; \
	fi
	@if [ ! -f $(TESTS_DIR)/test_main.py ]; then \
		echo "import pytest\nfrom main import create_app\n\ndef test_create_app():\n    app = create_app()\n    assert app is not None" > $(TESTS_DIR)/test_main.py; \
	fi
	@echo "$(GREEN)✅ Test structure created$(RESET)"

# =============================================================================
# Code Quality Commands (only if dev dependencies are available)
# =============================================================================

.PHONY: format
format: ## quality - Format code with black and isort
	@echo "$(BLUE)Formatting code...$(RESET)"
	@if command -v black >/dev/null 2>&1; then \
		black $(SRC_DIR) $(TESTS_DIR) main.py; \
		echo "$(GREEN)✅ Code formatted with black$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  black not found, skipping formatting$(RESET)"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort $(SRC_DIR) $(TESTS_DIR) main.py; \
		echo "$(GREEN)✅ Imports sorted with isort$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  isort not found, skipping import sorting$(RESET)"; \
	fi

.PHONY: lint
lint: ## quality - Run linting with flake8
	@echo "$(BLUE)Running linter...$(RESET)"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 $(SRC_DIR) $(TESTS_DIR) main.py; \
		echo "$(GREEN)✅ Linting completed$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  flake8 not found, install dev dependencies$(RESET)"; \
	fi

.PHONY: type-check
type-check: ## quality - Run type checking with mypy
	@echo "$(BLUE)Running type checker...$(RESET)"
	@if command -v mypy >/dev/null 2>&1; then \
		mypy $(SRC_DIR) main.py; \
		echo "$(GREEN)✅ Type checking completed$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  mypy not found, install dev dependencies$(RESET)"; \
	fi

# =============================================================================
# Docker Commands
# =============================================================================

.PHONY: docker-build
docker-build: ## docker - Build Docker image
	@echo "$(BLUE)Building Docker image...$(RESET)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

.PHONY: docker-run
docker-run: ## docker - Run Docker container
	@echo "$(BLUE)Running Docker container...$(RESET)"
	@if [ -f $(ENV_FILE) ]; then \
		docker run -p 8080:8080 --env-file $(ENV_FILE) $(DOCKER_IMAGE):$(DOCKER_TAG); \
	else \
		echo "$(YELLOW)⚠️  .env file not found, running without environment file$(RESET)"; \
		docker run -p 8080:8080 $(DOCKER_IMAGE):$(DOCKER_TAG); \
	fi

.PHONY: docker-run-cli
docker-run-cli: ## docker - Run Docker container in CLI mode
	@echo "$(BLUE)Running Docker container in CLI mode...$(RESET)"
	@if [ -f $(ENV_FILE) ]; then \
		docker run -it --env-file $(ENV_FILE) $(DOCKER_IMAGE):$(DOCKER_TAG) python main.py --mode cli; \
	else \
		docker run -it $(DOCKER_IMAGE):$(DOCKER_TAG) python main.py --mode cli; \
	fi

.PHONY: docker-stop
docker-stop: ## docker - Stop all running containers
	@echo "$(BLUE)Stopping containers...$(RESET)"
	@docker stop $$(docker ps -q --filter ancestor=$(DOCKER_IMAGE):$(DOCKER_TAG)) 2>/dev/null || echo "$(YELLOW)No containers to stop$(RESET)"

.PHONY: docker-clean
docker-clean: docker-stop ## docker - Clean up Docker images and containers
	@echo "$(BLUE)Cleaning up Docker resources...$(RESET)"
	@docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) 2>/dev/null || echo "$(YELLOW)Image not found$(RESET)"
	@docker system prune -f

# =============================================================================
# Docker Compose Commands
# =============================================================================

.PHONY: compose-up
compose-up: ## docker - Start full application stack with docker-compose
	@echo "$(BLUE)Starting full application stack...$(RESET)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)❌ .env file not found$(RESET)"; \
		echo "$(YELLOW)Run 'make setup-env' to create it$(RESET)"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) up -d --build
	@echo "$(GREEN)✅ Application stack started$(RESET)"
	@echo "$(CYAN)Use 'make compose-logs' to view logs$(RESET)"

.PHONY: compose-up-middleware
compose-up-middleware: ## docker - Start middleware services only (postgres, redis)
	@echo "$(BLUE)Starting middleware services...$(RESET)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)❌ .env file not found$(RESET)"; \
		echo "$(YELLOW)Run 'make setup-env' to create it$(RESET)"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) -f docker-compose.middleware.yml up -d
	@echo "$(GREEN)✅ Middleware services started$(RESET)"
	@echo "$(CYAN)Use 'make compose-logs-middleware' to view logs$(RESET)"

.PHONY: compose-down
compose-down: ## docker - Stop full application stack
	@echo "$(BLUE)Stopping full application stack...$(RESET)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Application stack stopped$(RESET)"

.PHONY: compose-down-middleware
compose-down-middleware: ## docker - Stop middleware services
	@echo "$(BLUE)Stopping middleware services...$(RESET)"
	$(DOCKER_COMPOSE) -f docker-compose.middleware.yml down
	@echo "$(GREEN)✅ Middleware services stopped$(RESET)"

.PHONY: compose-restart
compose-restart: compose-down compose-up ## docker - Restart full application stack

.PHONY: compose-restart-middleware
compose-restart-middleware: compose-down-middleware compose-up-middleware ## docker - Restart middleware services

.PHONY: compose-build
compose-build: ## docker - Build application image for docker-compose
	@echo "$(BLUE)Building application image...$(RESET)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✅ Application image built$(RESET)"

.PHONY: compose-logs
compose-logs: ## docker - View logs from full application stack
	@echo "$(BLUE)Viewing application stack logs...$(RESET)"
	$(DOCKER_COMPOSE) logs -f

.PHONY: compose-logs-middleware
compose-logs-middleware: ## docker - View logs from middleware services
	@echo "$(BLUE)Viewing middleware services logs...$(RESET)"
	$(DOCKER_COMPOSE) -f docker-compose.middleware.yml logs -f

.PHONY: compose-ps
compose-ps: ## docker - Show status of docker-compose services
	@echo "$(BLUE)Docker Compose Services Status:$(RESET)"
	@echo "$(CYAN)Full Stack:$(RESET)"
	@$(DOCKER_COMPOSE) ps 2>/dev/null || echo "$(YELLOW)No full stack services running$(RESET)"
	@echo ""
	@echo "$(CYAN)Middleware Only:$(RESET)"
	@$(DOCKER_COMPOSE) -f docker-compose.middleware.yml ps 2>/dev/null || echo "$(YELLOW)No middleware services running$(RESET)"

.PHONY: compose-clean
compose-clean: ## docker - Stop and remove all containers, networks, and volumes
	@echo "$(BLUE)Cleaning up docker-compose resources...$(RESET)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f docker-compose.middleware.yml down -v --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✅ Docker compose cleanup complete$(RESET)"

# =============================================================================
# Utility Commands
# =============================================================================

.PHONY: clean
clean: ## Clean build artifacts and cache files
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	@rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

.PHONY: clean-logs
clean-logs: ## Clean log files
	@echo "$(BLUE)Cleaning log files...$(RESET)"
	@rm -rf $(LOGS_DIR)/*.log 2>/dev/null || true
	@echo "$(GREEN)✅ Log files cleaned$(RESET)"

.PHONY: config-check
config-check: ## Validate configuration
	@echo "$(BLUE)Checking configuration...$(RESET)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)❌ .env file not found$(RESET)"; \
		echo "$(YELLOW)Run 'make setup-env' to create it$(RESET)"; \
		exit 1; \
	fi
	@$(PYTHON_CMD) -c "from src.core.config import settings; print('✅ Configuration valid')"

.PHONY: version
version: ## Show project version
	@echo "$(BLUE)Project version:$(RESET)"
	@$(PYTHON_CMD) -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

# =============================================================================
# Composite Commands
# =============================================================================

.PHONY: setup
setup: setup-deps setup-env setup-dirs test-create ## Complete project setup
	@echo "$(GREEN)✅ Project setup complete!$(RESET)"
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Edit .env file with your configuration"
	@echo "  2. Run 'make dev-start' to start development environment"
	@echo "  3. Run 'make run-cli' to test CLI mode"
	@echo "  4. Run 'make run-api' to start the API server"

.PHONY: dev-start
dev-start: compose-up-middleware ## Start development environment (middleware only)
	@echo "$(GREEN)✅ Development environment started!$(RESET)"
	@echo "$(YELLOW)Services available:$(RESET)"
	@echo "  - PostgreSQL: localhost:$${DB_PORT:-5432}"
	@echo "  - Redis: localhost:$${REDIS_PORT:-6379}"
	@echo "$(CYAN)Now you can run your application locally with 'make run-api' or 'make run-cli'$(RESET)"

.PHONY: dev-stop
dev-stop: compose-down-middleware ## Stop development environment
	@echo "$(GREEN)✅ Development environment stopped$(RESET)"

.PHONY: prod-start
prod-start: compose-up ## Start production-like environment (full stack)
	@echo "$(GREEN)✅ Production-like environment started!$(RESET)"
	@echo "$(CYAN)Application available at: http://localhost:$${APP_PORT:-8080}$(RESET)"

.PHONY: prod-stop
prod-stop: compose-down ## Stop production-like environment
	@echo "$(GREEN)✅ Production-like environment stopped$(RESET)"

# =============================================================================
# Special Targets
# =============================================================================

# Prevent make from deleting intermediate files
.SECONDARY: