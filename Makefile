.PHONY: install dev lint test train api hub alpha compose up cache-universe

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

lint:
	ruff check quant_core api tests mlops scripts

test:
	pytest --cov=quant_core --cov=api --cov-report=term-missing

train:
	python scripts/train_all.py

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

hub:
	streamlit run nexus-hub/app.py

alpha:
	streamlit run alpha-terminal/app.py

cache-universe:
	python scripts/cache_universe.py

compose:
	docker compose up --build

up: compose
