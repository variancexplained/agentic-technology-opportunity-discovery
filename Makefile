.PHONY: install test test-unit test-integration lint format clean

ENV_NAME := $(shell grep '^name:' environment.yml | awk '{print $$2}')

install:
	conda env create -f environment.yml
	@echo "Activate with: conda activate $(ENV_NAME)"

update:
	conda env update -f environment.yml --prune

test:
	pytest -v

test-unit:
	pytest -v -m unit

test-integration:
	pytest -v -m integration

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
