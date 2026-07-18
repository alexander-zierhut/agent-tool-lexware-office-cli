.PHONY: help install test test-unit lint docs clean
PY ?= python3
VENV ?= .venv

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create a venv and install the CLI (editable, with test deps)
	$(PY) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install -q -e '.[test]'

test: ## Run the full suite (integration tests need a backend; they skip without)
	. $(VENV)/bin/activate && python -m pytest

test-unit: ## Run the hermetic tests (no account, no backend, no token)
	# The MARKER is the source of truth, never a file list.
	. $(VENV)/bin/activate && python -m pytest -m "not integration"

lint: ## Lint with ruff (not a declared dep: pip install ruff, or use uvx/pipx)
	@command -v ruff >/dev/null 2>&1 || { echo "ruff not found. pip install ruff"; exit 1; }
	ruff check src tests scripts

docs: ## Regenerate docs/COMMANDS.md from the live command tree
	. $(VENV)/bin/activate && python scripts/gen_docs.py

clean: ## Remove build artifacts and caches
	rm -rf dist build *.egg-info src/*.egg-info .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
