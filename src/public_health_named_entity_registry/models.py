"""Small internal models used by the tooling, not a second registry schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Record:
    record_type: str
    class_name: str
    identifier: str
    data: dict[str, Any]
    path: Path


@dataclass(frozen=True, order=True)
class Issue:
    severity: Severity
    code: str
    message: str
    path: str = ""
    record_id: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "record_id": self.record_id,
        }


@dataclass
class RegistryData:
    records: list[Record] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def by_id(self) -> dict[str, Record]:
        return {record.identifier: record for record in self.records}

    def records_of_type(self, record_type: str) -> list[Record]:
        return [record for record in self.records if record.record_type == record_type]

    def as_registry(self, release: dict[str, Any]) -> dict[str, Any]:
        collections: dict[str, list[dict[str, Any]]] = {
            "entities": [],
            "relationships": [],
            "participations": [],
            "evidence": [],
        }
        from .config import RECORD_CONFIG

        for record in sorted(self.records, key=lambda item: item.identifier):
            collection = str(RECORD_CONFIG[record.record_type]["collection"])
            collections[collection].append(record.data)
        return {"release": release, **collections}
