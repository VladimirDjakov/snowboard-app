.PHONY: dev-up dev-down pull-models migrate test lint

dev-up:
	@docker-compose -f infra/docker-compose.yml up -d

dev-down:
	@docker-compose -f infra/docker-compose.yml down

pull-models:
	@bash infra/scripts/pull_models.sh

migrate:
	@alembic upgrade head

lint:
	@echo "Run linters here"

format:
	@echo "Run formatters here"

test:
	@echo "Run tests here"
