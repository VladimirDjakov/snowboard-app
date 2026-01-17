.PHONY: dev-up dev-down dev-build dev-up-force dev-rebuild pull-models migrate test lint lint-fix format

# Docker Compose configuration
DOCKER_COMPOSE = docker compose -f infra/docker-compose.yml
SERVICES = api worker-cpu

# UV configuration
UV_RUN = uv run --directory backend

# Environment variables
POSTGRES_USER ?= snowboard
POSTGRES_PASSWORD ?= snowboard_password
POSTGRES_DB ?= snowboard_db
POSTGRES_PORT ?= 5432

dev-up:
	@$(DOCKER_COMPOSE) up -d

dev-down:
	@$(DOCKER_COMPOSE) down

dev-build:
	@$(DOCKER_COMPOSE) build --no-cache $(SERVICES)

dev-up-force:
	@$(DOCKER_COMPOSE) up -d --force-recreate $(SERVICES)

dev-rebuild: dev-down dev-build dev-up-force

pull-models:
	@bash infra/scripts/pull_models.sh

migrate:
	@bash -c "DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB} \
	$(UV_RUN) alembic upgrade head"

lint:
	@$(UV_RUN) ruff check .

lint-fix:
	@$(UV_RUN) ruff check --fix .

format:
	@$(UV_RUN) ruff format .

test:
	@echo "Run tests here"
	@$(UV_RUN) pytest tests/
