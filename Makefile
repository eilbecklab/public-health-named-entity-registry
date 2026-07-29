.PHONY: install workbook test lint typecheck graph-check graph-init \
	graph-validate graph-stats graph-export all

install:
	python3 -m pip install -e ".[dev]"

workbook:
	python scripts/generate_intake_workbook.py

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy

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

all: test lint typecheck
