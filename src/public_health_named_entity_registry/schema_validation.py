"""Schema-driven structural validation using the authoritative LinkML YAML."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import project_root, schema_path
from .models import Issue, Record
from .yaml_io import load_yaml

BUILTIN_TYPES = {"string", "boolean", "decimal", "integer", "date", "datetime", "uri"}


class SchemaValidator:
    def __init__(self, root: Path | None = None) -> None:
        self.root = project_root(root)
        schema = load_yaml(schema_path(self.root))
        if not isinstance(schema, dict):
            raise ValueError("LinkML schema root must be a mapping")
        self.schema = schema
        self.classes = schema.get("classes", {})
        self.enums = schema.get("enums", {})
        self.types = schema.get("types", {})

    def validate_record(self, record: Record) -> list[Issue]:
        return self.validate_object(
            record.data,
            record.class_name,
            str(record.path),
            record.identifier,
            record.class_name,
        )

    def validate_object(
        self,
        value: Any,
        class_name: str,
        path: str,
        record_id: str,
        field_path: str,
    ) -> list[Issue]:
        issues: list[Issue] = []
        if not isinstance(value, dict):
            return [
                Issue(
                    "error",
                    "invalid-object",
                    f"{field_path} must be a mapping.",
                    path,
                    record_id,
                )
            ]
        class_def = self.classes.get(class_name, {})
        attributes = class_def.get("attributes", {})
        unknown = sorted(set(value) - set(attributes))
        for name in unknown:
            issues.append(
                Issue(
                    "error",
                    "unknown-field",
                    f"{field_path}.{name} is not defined by the LinkML schema.",
                    path,
                    record_id,
                )
            )
        for name, slot in attributes.items():
            present = name in value and value[name] is not None
            item = value.get(name)
            item_path = f"{field_path}.{name}"
            if slot.get("required") and not present:
                issues.append(
                    Issue(
                        "error",
                        "required-field",
                        f"{item_path} is required.",
                        path,
                        record_id,
                    )
                )
                continue
            if not present:
                continue
            if slot.get("multivalued"):
                if not isinstance(item, list):
                    issues.append(
                        Issue(
                            "error",
                            "expected-list",
                            f"{item_path} must be a list.",
                            path,
                            record_id,
                        )
                    )
                    continue
                if slot.get("required") and not item:
                    issues.append(
                        Issue(
                            "error",
                            "empty-required-list",
                            f"{item_path} must contain at least one value.",
                            path,
                            record_id,
                        )
                    )
                for index, list_item in enumerate(item):
                    issues.extend(
                        self.validate_range(
                            list_item,
                            str(slot.get("range", "string")),
                            path,
                            record_id,
                            f"{item_path}[{index}]",
                        )
                    )
            else:
                if slot.get("required") and isinstance(item, str) and not item.strip():
                    issues.append(
                        Issue(
                            "error",
                            "blank-required-field",
                            f"{item_path} cannot be blank.",
                            path,
                            record_id,
                        )
                    )
                issues.extend(
                    self.validate_range(
                        item,
                        str(slot.get("range", "string")),
                        path,
                        record_id,
                        item_path,
                    )
                )
        return issues

    def validate_range(
        self, value: Any, range_name: str, path: str, record_id: str, field_path: str
    ) -> list[Issue]:
        if range_name in self.classes:
            return self.validate_object(value, range_name, path, record_id, field_path)
        if range_name in self.enums:
            allowed = set(self.enums[range_name].get("permissible_values", {}))
            if not isinstance(value, str) or value not in allowed:
                return [
                    Issue(
                        "error",
                        "invalid-enum",
                        f"{field_path} must be one of: {', '.join(sorted(allowed))}.",
                        path,
                        record_id,
                    )
                ]
            return []
        if range_name in self.types:
            type_def = self.types[range_name]
            issues = self.validate_range(
                value, str(type_def.get("typeof", "string")), path, record_id, field_path
            )
            pattern = type_def.get("pattern")
            if (
                not issues
                and pattern
                and (not isinstance(value, str) or re.fullmatch(str(pattern), value) is None)
            ):
                issues.append(
                    Issue(
                        "error",
                        "pattern-mismatch",
                        f"{field_path} does not match {pattern}.",
                        path,
                        record_id,
                    )
                )
            return issues
        if range_name not in BUILTIN_TYPES:
            return [
                Issue(
                    "error",
                    "unknown-schema-range",
                    f"{field_path} uses unknown range {range_name}.",
                    path,
                    record_id,
                )
            ]
        valid = _valid_builtin(value, range_name)
        return (
            []
            if valid
            else [
                Issue(
                    "error",
                    "invalid-type",
                    f"{field_path} is not a valid {range_name}.",
                    path,
                    record_id,
                )
            ]
        )


def _valid_builtin(value: Any, range_name: str) -> bool:
    if range_name == "string":
        return isinstance(value, str)
    if range_name == "boolean":
        return isinstance(value, bool)
    if range_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if range_name == "decimal":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if range_name == "date":
        if isinstance(value, dt.datetime):
            return False
        if isinstance(value, dt.date):
            return True
        try:
            dt.date.fromisoformat(value)
            return isinstance(value, str)
        except (TypeError, ValueError):
            return False
    if range_name == "datetime":
        if isinstance(value, dt.datetime):
            return True
        try:
            dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return isinstance(value, str)
        except (AttributeError, TypeError, ValueError):
            return False
    if range_name == "uri":
        if not isinstance(value, str):
            return False
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    return False
