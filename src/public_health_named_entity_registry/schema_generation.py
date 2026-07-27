"""Generate LinkML-derived artifacts through the official generators."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import schema_path


class GenerationError(RuntimeError):
    pass


def _run(command: list[str], root: Path, output: Path | None = None) -> None:
    executable = shutil.which(command[0])
    environment_executable = Path(sys.executable).parent / command[0]
    if executable is None and environment_executable.is_file():
        executable = str(environment_executable)
    if executable is None:
        raise GenerationError(
            f"{command[0]} is unavailable; install development dependencies with "
            '`python -m pip install -e ".[dev]"`.'
        )
    result = subprocess.run(
        [executable, *command[1:]],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise GenerationError(
            f"{' '.join(command)} failed:\n{result.stderr or result.stdout}".rstrip()
        )
    if output is not None:
        rendered = re.sub(
            r"^# Generation date: .+$",
            "# Generation date: normalized for reproducible builds",
            result.stdout,
            count=1,
            flags=re.MULTILINE,
        )
        output.write_text(rendered, encoding="utf-8")


def generate_schema_artifacts(root: Path, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    schema = schema_path(root)
    json_schema = destination / "registry.schema.json"
    python_model = destination / "registry_models.py"
    docs = destination / "docs"
    if docs.exists():
        shutil.rmtree(docs)
    _run(["gen-json-schema", "--closed", str(schema)], root, json_schema)
    _run(["gen-python", "--validate", str(schema)], root, python_model)
    _run(["gen-doc", str(schema), "-d", str(docs)], root)
    return [json_schema, python_model, docs]
