.PHONY: install dev lint typecheck test migrate migration prod up down logs lock

install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

# Generate a reproducible dependency lockfile. Run this in the SAME Python
# version as production (python:3.12) — a lock built on a different version
# can contain wheels that don't exist for 3.12 and break the Docker build.
lock:
	pip install pip-tools
	pip-compile --annotate --no-header --output-file requirements.lock requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers

lint:
	ruff check app/ tests/

typecheck:
	mypy app/ tests/

test:
	pytest tests/ -v --cov=app --cov-report=term

test-coverage:
	pytest tests/ -v --cov=app --cov-report=html

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(message)"

rollback-migration:
	alembic downgrade -1

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

.PHONY: install dev prod lint typecheck test test-coverage migrate migration up down logs
