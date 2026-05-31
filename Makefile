.PHONY: dev stop build seed reset-db test logs clean

dev: ## Start development environment
	docker compose up --build

stop: ## Stop all containers
	docker compose down

build: ## Rebuild containers without cache
	docker compose build --no-cache

seed: ## Seed the database with sample data
	docker compose exec backend python -c "from database.init_db import main; main()"

reset-db: ## Delete SQLite database and re-seed
	rm -f backend/data/tenet.db
	$(MAKE) seed

test: ## Run backend tests
	docker compose exec backend python -m pytest

logs: ## Tail container logs
	docker compose logs -f

clean: ## Remove all containers, volumes, and built images
	docker compose down -v --rmi local

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
