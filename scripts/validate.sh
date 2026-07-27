#!/usr/bin/env bash
set -euo pipefail

phner validate registry
phner find-duplicates
pytest

