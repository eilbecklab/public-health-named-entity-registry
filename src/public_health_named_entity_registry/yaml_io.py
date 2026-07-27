"""Deterministic YAML/JSON helpers."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml


class PhnerDumper(yaml.SafeDumper):
    """Safe dumper that consistently renders dates and preserves key order."""


def _represent_date(dumper: yaml.SafeDumper, value: dt.date) -> yaml.Node:
    return dumper.represent_scalar("tag:yaml.org,2002:timestamp", value.isoformat())


PhnerDumper.add_representer(dt.date, _represent_date)
PhnerDumper.add_representer(dt.datetime, _represent_date)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def dump_yaml(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.dump(
        data,
        Dumper=PhnerDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    path.write_text(rendered, encoding="utf-8")


def json_default(value: Any) -> str:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def dump_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, default=json_default, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def normalized_json(data: Any) -> str:
    return json.dumps(data, default=json_default, ensure_ascii=False, sort_keys=True)
