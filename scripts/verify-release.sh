#!/usr/bin/env bash
set -euo pipefail

phner release verify "${1:-build/}"

