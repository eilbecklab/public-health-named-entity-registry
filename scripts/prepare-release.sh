#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/prepare-release.sh VERSION" >&2
  exit 2
fi

phner release prepare --version "$1"
phner release verify build/

