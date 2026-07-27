"""Temporal consistency checks."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from typing import Any

from .models import Issue, Record


def _date(value: Any) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _walk(value: Any, path: str) -> Iterator[tuple[dict[str, Any], str]]:
    if isinstance(value, dict):
        yield value, path
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def validate_temporal(record: Record) -> list[Issue]:
    issues: list[Issue] = []
    for item, field_path in _walk(record.data, record.class_name):
        if "valid_from" not in item and "valid_to" not in item:
            continue
        start = _date(item.get("valid_from"))
        end = _date(item.get("valid_to"))
        if start is not None and end is not None and end < start:
            issues.append(
                Issue(
                    "error",
                    "invalid-interval",
                    f"{field_path}.valid_to is earlier than valid_from.",
                    str(record.path),
                    record.identifier,
                )
            )
    return issues


def is_current(data: dict[str, Any], on_date: dt.date | None = None) -> bool:
    on_date = on_date or dt.date.today()
    start = _date(data.get("valid_from"))
    end = _date(data.get("valid_to"))
    return (start is None or start <= on_date) and (end is None or end >= on_date)
