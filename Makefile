.PHONY: up down build migrate logs ps shell-api shell-worker

# ─── Core ─────────────────────────────────────────────────────────────────────

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

restart:
	docker compose restart

ps:
	docker compose ps

# ─── Logs ────────────────────────────────────────────────────────────────────

logs:
	docker compose logs -f --tail=100

logs-api:
	docker compose logs -f api --tail=100

logs-worker:
	docker compose logs -f worker --tail=100

logs-bot:
	docker compose logs -f bot --tail=100

# ─── Migration ───────────────────────────────────────────────────────────────

migrate:
	docker compose --profile migrate run --rm migrate

migrate-only:
	docker compose --profile migrate run --rm migrate sh -c "alembic -c api/alembic.ini upgrade head"

# ─── Dev shells ──────────────────────────────────────────────────────────────

shell-api:
	docker compose exec api bash

shell-worker:
	docker compose exec worker bash

shell-pg:
	docker compose exec postgres psql -U aislide -d aislide

# ─── Alembic ─────────────────────────────────────────────────────────────────

migration-new:
	docker compose exec api alembic -c api/alembic.ini revision --autogenerate -m "$(MSG)"

migration-up:
	docker compose exec api alembic -c api/alembic.ini upgrade head

migration-down:
	docker compose exec api alembic -c api/alembic.ini downgrade -1
