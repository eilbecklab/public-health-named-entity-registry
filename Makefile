.PHONY: install validate-schema validate-data test lint typecheck generate quality-report all

install:
	python3 -m pip install -e ".[dev]"

validate-schema:
	linkml-validate src/public_health_named_entity_registry/schema/public_health_named_entity_registry.yaml
	phner generate-schema

validate-data:
	phner validate registry

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy

generate:
	phner build

quality-report:
	phner review registry

all: validate-data test lint typecheck generate
