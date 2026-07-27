"""Deterministic flattened CSV exports."""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .models import RegistryData


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(
            value,
            default=lambda item: item.isoformat(),
            ensure_ascii=False,
            sort_keys=True,
        )
    return str(value)


def export_csv(registry: RegistryData, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    mapping = {
        "entity": "entities.csv",
        "relationship": "relationships.csv",
        "participation": "participations.csv",
        "source": "evidence.csv",
    }
    for record_type, filename in mapping.items():
        records = sorted(registry.records_of_type(record_type), key=lambda item: item.identifier)
        fields = sorted({key for record in records for key in record.data})
        path = destination / filename
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            if fields:
                writer.writeheader()
                for record in records:
                    writer.writerow({field: _cell(record.data.get(field)) for field in fields})
        outputs.append(path)
    return outputs
