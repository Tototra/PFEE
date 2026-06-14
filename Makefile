# ============================================================================
# Coach IA GTB — Makefile
# Usage : make help
# ============================================================================

.PHONY: help up down build logs ps test test-backend test-frontend lint lint-backend lint-frontend format seed migrate shell-backend shell-db clean install-backend install-frontend

DOCKER_COMPOSE := docker compose

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# -------- Lifecycle Docker --------

up: ## Démarre toute la stack en dev (postgres, redis, backend, frontend)
	$(DOCKER_COMPOSE) up -d
	@echo "✓ Backend  : http://localhost:8000/docs"
	@echo "✓ Frontend : http://localhost:5173"

down: ## Stoppe et supprime les conteneurs
	$(DOCKER_COMPOSE) down

build: ## Rebuild les images sans cache
	$(DOCKER_COMPOSE) build --no-cache

logs: ## Tail logs de tous les services
	$(DOCKER_COMPOSE) logs -f --tail=100

ps: ## Liste les services et leur état
	$(DOCKER_COMPOSE) ps

# -------- Base de données --------

migrate: ## Applique le schéma SQL TimescaleDB
	$(DOCKER_COMPOSE) exec -T postgres psql -U coachia -d coachia < infra/sql/01_timescale_schema.sql

seed: ## Insère des données de démo dans la base
	$(DOCKER_COMPOSE) exec backend python -m scripts.seed_demo_data

shell-db: ## Ouvre un psql sur la base
	$(DOCKER_COMPOSE) exec postgres psql -U coachia -d coachia

# -------- Tests --------

test: test-backend test-frontend ## Lance tous les tests

test-backend: ## Tests pytest backend
	$(DOCKER_COMPOSE) exec backend pytest -v

test-frontend: ## Tests frontend
	$(DOCKER_COMPOSE) exec frontend npm test

# -------- Qualité de code --------

lint: lint-backend lint-frontend ## Lint backend + frontend

lint-backend: ## Lint Python (ruff)
	$(DOCKER_COMPOSE) exec backend ruff check app/ scripts/ tests/

lint-frontend: ## Lint TypeScript (eslint)
	$(DOCKER_COMPOSE) exec frontend npm run lint

format: ## Formate le code Python (ruff format)
	$(DOCKER_COMPOSE) exec backend ruff format app/ scripts/ tests/

# -------- Shells --------

shell-backend: ## Shell bash dans le conteneur backend
	$(DOCKER_COMPOSE) exec backend /bin/bash

# -------- Setup local (sans Docker) --------

install-backend: ## Installe les deps backend en local (Python 3.11+)
	cd backend && pip install -e ".[dev]"

install-frontend: ## Installe les deps frontend en local (Node 20+)
	cd frontend && npm install

# -------- Nettoyage --------

clean: ## Supprime conteneurs, volumes, caches Python et node_modules
	$(DOCKER_COMPOSE) down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/node_modules frontend/dist
	rm -rf backend/.ruff_cache backend/data/chroma

.DEFAULT_GOAL := help
