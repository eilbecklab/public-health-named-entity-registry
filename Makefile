.PHONY: install graph-check graph-init graph-validate graph-stats graph-export \
	validate-schema validate-interchange test lint typecheck generate-interchange all

install:
	python3 -m pip install -e ".[dev]"

validate-schema:
	linkml-validate src/public_health_named_entity_registry/schema/public_health_named_entity_registry.yaml
	phner generate-schema

graph-check:
	phner graph check

graph-init:
	phner graph init

graph-validate:
	phner graph validate

graph-stats:
	phner graph stats

graph-export:
	phner graph export

validate-interchange:
	phner validate registry

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy

generate-interchange:
	phner build

all: validate-schema test lint typecheck
