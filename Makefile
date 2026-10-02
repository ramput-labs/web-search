# web-search: FastAPI server (repo root: web_search/) + SvelteKit chat UI (ui/)
# Run `make` for the list of targets.

SHELL := /bin/bash
.DEFAULT_GOAL := help

-include .env
export

HOST    ?= 127.0.0.1
PORT    ?= 8009
UI_HOST ?= 127.0.0.1
UI_PORT ?= 5173

PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python
UI     := ui
BUN    := cd $(UI) && bun
SERVER_URL := http://$(HOST):$(PORT)

.PHONY: help install venv env dev dev-server dev-ui build start server ui test lint format check clean distclean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: venv ## Install server and UI dependencies
	$(BUN) install --frozen-lockfile

# pip runs again only when requirements.txt is newer than the last install
$(VENV)/.installed: requirements.txt
	@# a venv without pip (one made by uv, say) cannot install requirements; start it over
	@$(PY) -m pip --version >/dev/null 2>&1 || { rm -rf $(VENV); $(PYTHON) -m venv $(VENV); }
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements.txt
	@touch $@

venv: $(VENV)/.installed ## Create .venv and install the server's requirements

env: ## Create .env from .env.example (keeps an existing one)
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "created .env")

# --- development -------------------------------------------------------------

# Each process gets its own process group (set -m) and exactly one SIGTERM on Ctrl-C: uvicorn's reload supervisor
# deadlocks when a second signal lands inside its handler.
define run_both
	@set -m; \
	( $(1) ) & first=$$!; \
	( $(2) ) & second=$$!; \
	trap 'kill -TERM -$$first -$$second 2>/dev/null' INT TERM; \
	wait; wait
endef

SERVER := exec $(PY) -m web_search

dev: venv ## Run server and UI with live reload (Ctrl-C stops both)
	$(call run_both,RELOAD=1 $(SERVER),$(DEV_UI))

dev-server: venv ## Run the FastAPI server with auto-reload
	RELOAD=1 $(SERVER)

dev-ui: ## Run the SvelteKit dev server
	$(DEV_UI)

DEV_UI = cd $(UI) && WEB_SEARCH_URL=$(SERVER_URL) exec bun run dev --host $(UI_HOST) --port $(UI_PORT)

# --- production --------------------------------------------------------------

build: ## Build the UI into ui/build (Node server); the server runs from source
	$(BUN) run build

start: venv ## Run server and UI in production mode (after `make build`)
	@test -d $(UI)/build || { echo "ui/build is missing; run 'make build' first"; exit 1; }
	$(call run_both,$(SERVER),$(START_UI))

server: venv ## Run the FastAPI server (production settings)
	$(SERVER)

ui: ## Serve the built UI with Node
	@test -d $(UI)/build || { echo "ui/build is missing; run 'make build' first"; exit 1; }
	$(START_UI)

START_UI = cd $(UI) && WEB_SEARCH_URL=$(SERVER_URL) HOST=$(UI_HOST) PORT=$(UI_PORT) \
	ORIGIN=http://$(UI_HOST):$(UI_PORT) exec node build

# --- quality -----------------------------------------------------------------

test: venv ## Run the server and UI tests
	$(PY) -m pytest tests
	$(BUN) test src

lint: venv ## Lint server (ruff) and UI (prettier, eslint)
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(BUN) run lint

format: venv ## Format server and UI code
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .
	$(BUN) run format

check: lint test ## Lint, type-check the UI and run the tests
	$(BUN) run check

# --- cleanup -----------------------------------------------------------------

clean: ## Remove build output and caches
	rm -rf $(UI)/build $(UI)/.svelte-kit .pytest_cache .ruff_cache
	find web_search tests -name __pycache__ -type d -prune -exec rm -rf {} +

distclean: clean ## Also remove installed dependencies
	rm -rf $(UI)/node_modules $(VENV)
