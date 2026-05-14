COMPOSE ?= docker compose
LOCAL_DB ?= backend/data/tenet.db

.PHONY: dev stop down build seed reset-db test backend-test frontend-test logs clean shell help

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

test: backend-test frontend-test ## Run backend tests and frontend build check

backend-test: ## Run backend pytest suite
	$(COMPOSE) run --rm -e DB_PATH=/tmp/tenet-test.db backend python -m pytest

frontend-test: ## Run frontend build check
	$(COMPOSE) run --rm frontend npm run build

logs: ## Tail container logs
	$(COMPOSE) logs -f

clean: ## Remove all containers, volumes, and built images
	$(COMPOSE) down -v --rmi local --remove-orphans

shell: ## Open a shell in the backend container
	$(COMPOSE) run --rm backend sh

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
