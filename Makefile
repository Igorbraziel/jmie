# ==============================================================================
# JMIE Environment Configuration
# ==============================================================================

COMPOSE_BASE := docker-compose.yml
COMPOSE_DEV  := docker-compose.dev.yml
COMPOSE_PROD := docker-compose.prod.yml

ENV_DEV  := .env.dev
ENV_PROD := .env.prod

# ==============================================================================
# Local Development (Uses .env.dev and docker-compose.dev.yml)
# ==============================================================================

.PHONY: up-dev
up-dev: ## Start the development stack in the background
	docker compose --env-file $(ENV_DEV) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) up -d --build

.PHONY: down-dev
down-dev: ## Stop and remove the development stack
	docker compose --env-file $(ENV_DEV) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) down

.PHONY: logs-dev
logs-dev: ## Tail logs for the development stack (use svc=fastapi-app to filter)
	docker compose --env-file $(ENV_DEV) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) logs -f $(svc)

# ==============================================================================
# Production (Uses .env.prod and docker-compose.prod.yml)
# ==============================================================================

.PHONY: up-prod
up-prod: ## Start the production stack in the background
	docker compose --env-file $(ENV_PROD) -f $(COMPOSE_BASE) -f $(COMPOSE_PROD) up -d

.PHONY: down-prod
down-prod: ## Stop and remove the production stack
	docker compose --env-file $(ENV_PROD) -f $(COMPOSE_BASE) -f $(COMPOSE_PROD) down

.PHONY: logs-prod
logs-prod: ## Tail logs for the production stack
	docker compose --env-file $(ENV_PROD) -f $(COMPOSE_BASE) -f $(COMPOSE_PROD) logs -f $(svc)

# ==============================================================================
# Database & Alembic Utilities (Runs locally via uv)
# ==============================================================================

.PHONY: migrate
migrate: ## Run Alembic migrations to update the database to the latest schema
	uv run alembic upgrade head

.PHONY: downgrade
downgrade: ## Undo the last Alembic migration
	uv run alembic downgrade -1

.PHONY: revision
revision: ## Generate a new Alembic migration (Usage: make revision m="add_new_table")
	uv run alembic revision -m "$(m)"

# ==============================================================================
# Help Menu
# ==============================================================================

.PHONY: help
help: ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help