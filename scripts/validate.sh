#!/usr/bin/env bash
set -euo pipefail

pytest
ruff check .
mypy

if [[ -n "${NEO4J_PASSWORD:-}" ]]; then
  phner graph check
  phner graph validate
else
  echo "NEO4J_PASSWORD is not set; skipping live graph validation."
fi
