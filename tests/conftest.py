from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def empty_project(tmp_path: Path, repository_root: Path) -> Path:
    for name in ["src", "templates", "mappings", ".phner"]:
        shutil.copytree(repository_root / name, tmp_path / name)
    for name in ["entities", "relationships", "participations", "evidence", "candidates"]:
        (tmp_path / "data" / name).mkdir(parents=True)
    (tmp_path / "releases").mkdir()
    return tmp_path


@pytest.fixture
def valid_project(empty_project: Path, repository_root: Path) -> Path:
    fixture_data = repository_root / "tests" / "fixtures" / "valid" / "data"
    for directory in ["entities", "relationships", "participations", "evidence"]:
        for source in (fixture_data / directory).glob("*.yaml"):
            shutil.copy2(source, empty_project / "data" / directory / source.name)
    return empty_project
