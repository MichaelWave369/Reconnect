.PHONY: dev lint test run

dev:
	python -m pip install -r requirements-dev.txt

lint:
	ruff format --check .
	ruff check .

test:
	pytest -q

run:
	python main.py
