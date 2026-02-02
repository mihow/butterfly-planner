# Makefile for Claude-First Python Template
#
# Usage:
#   make help       - Show available commands
#   make install    - Install dependencies
#   make test       - Run tests
#   make lint       - Run linting
#   make format     - Format code
#   make all        - Run all checks (lint, typecheck, test)

.PHONY: help install install-dev test test-cov lint format typecheck clean build docker-test docker-dev all

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Claude-First Python Template$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Installation
# =============================================================================

install: ## Install production dependencies
	uv pip install -e .

install-dev: ## Install development dependencies
	uv pip install -e ".[dev]"

# =============================================================================
# Testing
# =============================================================================

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage report (local)
	pytest --cov=my_project --cov-report=html --cov-report=term

test-ci: ## Run tests with coverage for CI (xml output)
	pytest -v --cov=my_project --cov-report=xml --cov-report=term

test-fast: ## Run tests excluding slow tests
	pytest -m "not slow"

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linter (ruff check)
	ruff check src tests

lint-fix: ## Run linter and fix issues
	ruff check --fix src tests

format: ## Format code with ruff
	ruff format src tests

format-check: ## Check formatting without changes
	ruff format --check src tests

typecheck: ## Run type checker (mypy)
	mypy src

# =============================================================================
# Combined Checks
# =============================================================================

all: lint typecheck test ## Run all checks (lint, typecheck, test)

check: lint format-check typecheck ## Run all checks without tests

ci: lint format-check typecheck test-cov ## Run CI pipeline locally

# =============================================================================
# Build
# =============================================================================

build: ## Build package
	python -m build

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# Docker
# =============================================================================

docker-test: ## Run tests in Docker
	docker compose run --rm test

docker-lint: ## Run linting in Docker
	docker compose run --rm lint

docker-dev: ## Start development shell in Docker
	docker compose run --rm dev

docker-build: ## Build production Docker image
	docker build -t my-project --target production .

docker-clean: ## Remove Docker containers and volumes
	docker compose down -v --remove-orphans

# =============================================================================
# Development
# =============================================================================

run: ## Run the CLI info command
	my-project info

setup: install-dev ## Full development setup
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "Run 'make test' to verify installation"

# =============================================================================
# Verification (CRITICAL - run before declaring done)
# =============================================================================

verify: ## Run full verification suite (imports, tests, smoke, CLI)
	@echo "$(BLUE)=== Level 1: Import Check ===$(NC)"
	python -c "from my_project import *; print('$(GREEN)imports ok$(NC)')"
	@echo ""
	@echo "$(BLUE)=== Level 2: Unit Tests ===$(NC)"
	pytest -x -q
	@echo ""
	@echo "$(BLUE)=== Level 3: Smoke Tests ===$(NC)"
	pytest tests/test_smoke.py -v
	@echo ""
	@echo "$(BLUE)=== Level 4: CLI Execution ===$(NC)"
	python -m my_project.cli info
	python -m my_project.cli run --name verify-test
	@echo ""
	@echo "$(GREEN)=== VERIFICATION PASSED ===$(NC)"

verify-mcp: ## Verify MCP servers are installed and working
	@echo "$(BLUE)Checking Chrome DevTools MCP...$(NC)"
	@npx @anthropic/mcp-server-chrome-devtools --help >/dev/null 2>&1 && echo "$(GREEN)chrome-devtools: OK$(NC)" || echo "$(YELLOW)chrome-devtools: NOT INSTALLED (run: npm install -g @anthropic/mcp-server-chrome-devtools)$(NC)"
	@echo ""
	@echo "$(BLUE)Checking Python LSP...$(NC)"
	@which pylsp >/dev/null 2>&1 && echo "$(GREEN)pylsp: OK ($(shell which pylsp))$(NC)" || echo "$(YELLOW)pylsp: NOT INSTALLED (run: uv pip install python-lsp-server[all])$(NC)"

# =============================================================================
# MCP Servers
# =============================================================================

mcp-install: ## Install MCP server dependencies
	npm install -g @anthropic/mcp-server-chrome-devtools
	uv pip install python-lsp-server[all]
	@echo "$(GREEN)MCP servers installed$(NC)"
