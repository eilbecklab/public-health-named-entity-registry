"""Durable, collision-aware PHNER identifier reservation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .config import RECORD_CONFIG, project_root
from .yaml_io import dump_yaml, load_yaml


class IdentifierError(RuntimeError):
    pass


def _ledger_path(root: Path) -> Path:
    return root / ".phner" / "id-reservations.yaml"


def _maximum_existing(root: Path, record_type: str) -> int:
    config = RECORD_CONFIG[record_type]
    prefix = str(config["prefix"])
    pattern = re.compile(rf"^{re.escape(prefix)}([0-9]{{6}})$")
    maximum = 0
    directory = root / "data" / str(config["directory"])
    for path in directory.glob("*.yaml"):
        try:
            data = load_yaml(path)
        except OSError:
            continue
        if not isinstance(data, dict):
            continue
        candidate = data.get(str(config["id_field"]))
        match = pattern.fullmatch(candidate) if isinstance(candidate, str) else None
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


def reserve_id(record_type: str, root: Path | None = None) -> str:
    if record_type not in RECORD_CONFIG:
        raise IdentifierError(f"Unknown record type: {record_type}")
    root = project_root(root)
    ledger_path = _ledger_path(root)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.with_suffix(".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise IdentifierError(
            f"Identifier ledger is locked at {lock_path}; remove it only if no "
            "phner process is active."
        ) from error
    try:
        os.close(lock_fd)
        raw: Any = load_yaml(ledger_path) if ledger_path.exists() else {}
        ledger = raw if isinstance(raw, dict) else {}
        last_reserved = ledger.get(record_type, 0)
        if not isinstance(last_reserved, int):
            raise IdentifierError(f"Invalid {record_type} counter in {ledger_path}")
        sequence = max(last_reserved, _maximum_existing(root, record_type)) + 1
        if sequence > 999_999:
            raise IdentifierError(f"Identifier space exhausted for {record_type}")
        ledger[record_type] = sequence
        ordered = {key: int(ledger.get(key, 0)) for key in RECORD_CONFIG}
        temporary = ledger_path.with_suffix(".tmp")
        dump_yaml(ordered, temporary)
        os.replace(temporary, ledger_path)
        return f"{RECORD_CONFIG[record_type]['prefix']}{sequence:06d}"
    finally:
        lock_path.unlink(missing_ok=True)
