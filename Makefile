.PHONY: up down logs test format

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend worker frontend

test:
	cd backend && python -m pytest

format:
	cd backend && python -m ruff check . --fix
