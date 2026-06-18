COMPOSE ?= docker compose
LOCAL_DB ?= backend/data/tenet.db
API_URL ?= http://127.0.0.1:5001

.PHONY: dev stop down build seed reset-db test backend-test frontend-test frontend-build frontend-typecheck backend-lint docker-build e2e smoke logs clean shell help

dev: ## Build, seed if needed, and start development environment
	$(COMPOSE) build
	@if [ ! -f "$(LOCAL_DB)" ]; then $(MAKE) seed; fi
	$(COMPOSE) up --build

stop: ## Stop all containers
	$(COMPOSE) down

down: stop ## Alias for stop

build: ## Rebuild containers without cache
	$(COMPOSE) build --no-cache

seed: ## Seed the local SQLite database
	$(COMPOSE) run --rm backend python -c "from database.init_db import main; main()"

reset-db: ## Delete SQLite database and re-seed
	$(COMPOSE) down
	rm -f $(LOCAL_DB)
	$(MAKE) seed

test: backend-test frontend-test ## Run backend and frontend test suites

backend-test: ## Run backend pytest suite
	$(COMPOSE) run --rm -e DB_PATH=/tmp/tenet-test.db backend python -m pytest

frontend-test: ## Run frontend Vitest suite
	$(COMPOSE) run --rm frontend npm run test

frontend-build: ## Run frontend production build
	$(COMPOSE) run --rm frontend npm run build

frontend-typecheck: ## Run frontend TypeScript checks
	$(COMPOSE) run --rm frontend npm run typecheck

backend-lint: ## Run minimal backend lint checks
	$(COMPOSE) run --rm backend python -m flake8 . --exclude venv,data,__pycache__

docker-build: ## Build backend and frontend Docker images
	$(COMPOSE) build backend frontend

e2e: ## Run Playwright end-to-end smoke tests against a running app
	cd frontend && npm run e2e

smoke: ## Run lightweight deployment smoke checks against a running backend
	$(COMPOSE) config >/dev/null
	cd frontend && npm run build
	curl -fsS "$(API_URL)/api/health" >/dev/null
	curl -fsS "$(API_URL)/api/cat/regions/summary" >/dev/null

logs: ## Tail container logs
	$(COMPOSE) logs -f

clean: ## Remove all containers, volumes, and built images
	$(COMPOSE) down -v --rmi local --remove-orphans

shell: ## Open a shell in the backend container
	$(COMPOSE) run --rm backend sh

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
