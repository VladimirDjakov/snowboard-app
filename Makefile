.PHONY: dev-up dev-down pull-models migrate test lint

dev-up:
	@docker compose -f infra/docker-compose.yml up -d

dev-down:
	@docker compose -f infra/docker-compose.yml down

pull-models:
	@bash infra/scripts/pull_models.sh

migrate:
	@alembic upgrade head

lint:
	@echo "Running ruff linter..."
	@bash tools/format.sh lint

format:
	@echo "Running ruff formatter..."
	@bash tools/format.sh format

format-check:
	@echo "Checking code formatting..."
	@bash tools/format.sh format-check

test:
	@echo "Run tests here"
