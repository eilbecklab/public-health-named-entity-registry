"""Create curator records from commented templates without inferring facts."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

from .config import RECORD_CONFIG, project_root
from .identifiers import reserve_id


class ScaffoldingError(RuntimeError):
    pass


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not value:
        raise ScaffoldingError("name slug must contain at least one letter or digit")
    return value


def new_record(
    record_type: str,
    root: Path | None = None,
    name_slug: str | None = None,
    supplied: dict[str, str] | None = None,
    created_by: str | None = None,
) -> Path:
    if record_type not in RECORD_CONFIG:
        raise ScaffoldingError(f"Unknown record type: {record_type}")
    root = project_root(root)
    config = RECORD_CONFIG[record_type]
    identifier = reserve_id(record_type, root)
    template_path = root / "templates" / str(config["template"])
    try:
        text = template_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ScaffoldingError(f"Cannot read template {template_path}: {error}") from error
    placeholder = f"{config['prefix']}000000"
    if placeholder not in text:
        raise ScaffoldingError(f"Template {template_path} lacks placeholder {placeholder}")
    text = text.replace(placeholder, identifier, 1)
    for field, value in (supplied or {}).items():
        pattern = re.compile(rf"^({re.escape(field)}):[ \t]*$", re.MULTILINE)
        yaml_scalar = json.dumps(value, ensure_ascii=False)
        text, replacements = pattern.subn(rf"\1: {yaml_scalar}", text, count=1)
        if replacements != 1:
            raise ScaffoldingError(f"Template does not have an empty scalar field {field}")
    if created_by is not None and "  created_by:\n" in text:
        text = text.replace("  created_by:\n", f"  created_by: {created_by}\n", 1)
        created_at = (
            dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
        text = text.replace("  created_at:\n", f"  created_at: {created_at}\n", 1)
    filename = identifier
    if name_slug:
        filename = f"{identifier}--{slugify(name_slug)}"
    destination = root / "data" / str(config["directory"]) / f"{filename}.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(destination, flags, 0o644)
    except FileExistsError as error:
        raise ScaffoldingError(f"Refusing to overwrite {destination}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
    return destination
