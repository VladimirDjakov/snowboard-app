.PHONY: dev-up dev-down pull-models migrate test lint loadenv

POSTGRES_USER ?= snowboard
POSTGRES_PASSWORD ?= snowboard_password
POSTGRES_DB ?= snowboard_db
POSTGRES_PORT ?= 5432

dev-up:
	@docker compose -f infra/docker-compose.yml up -d

dev-down:
	@docker compose -f infra/docker-compose.yml down

pull-models:
	@bash infra/scripts/pull_models.sh

migrate:
	@bash -c "DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB} \
	uv run --directory backend alembic upgrade head"
lint:
	@uv run --directory backend ruff check .

lint-fix:
	@uv run --directory backend ruff check --fix .

format:
	@uv run --directory backend ruff format .

test:
	@echo "Run tests here"
	@uv run --directory backend pytest tests/
