RELEASE_VERSION ?= 0.1.0
SHELL = bash


unit-test:
	poetry run python -m pytest -m 'not integration'

integration-test:
	poetry run python -m pytest -m 'integration'

build: clean lint
	poetry build

clean:
	rm -rf dist

lint-fix:
	poetry run python -m black .

lint:
	poetry run python -m black . --check

install:
	poetry install
