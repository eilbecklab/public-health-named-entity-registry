from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook


def test_committed_intake_workbook_matches_generator(tmp_path: Path) -> None:
    generated = tmp_path / "phner-intake-template.xlsx"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_intake_workbook.py",
            "--output",
            str(generated),
        ],
        check=True,
    )

    workbook = load_workbook(generated)
    assert workbook.sheetnames == [
        "Instructions",
        "Entities",
        "Relationships",
        "Sources",
        "Names",
        "Locations",
        "Platform Participations",
        "Relationship Guide",
        "Lookup Values",
        "Examples",
    ]
    assert workbook["Entities"]["A1"].value == "intake_key *"
    assert workbook["Entities"]["C1"].value == "entity_type *"
    assert workbook["Relationships"]["C1"].value == "relationship_type *"
    assert workbook["Sources"]["B1"].value == "source_type *"
    assert "EntityTypes" in workbook.defined_names
    assert "RelationshipTypes" in workbook.defined_names
    assert "EntityKeys" in workbook.defined_names
    assert len(workbook["Entities"].data_validations.dataValidation) >= 3
    assert len(workbook["Relationships"].data_validations.dataValidation) >= 4


def test_committed_template_can_be_opened(repository_root: Path) -> None:
    path = repository_root / "templates" / "phner-intake-template.xlsx"
    workbook = load_workbook(path, read_only=False, data_only=False)
    assert workbook.properties.title == "PHNER graph intake workbook"
    assert workbook["Instructions"]["A1"].value == "PHNER graph intake workbook"


def test_versioned_working_workbook_can_be_opened(repository_root: Path) -> None:
    path = repository_root / "intake" / "phner-intake.xlsx"
    workbook = load_workbook(path, read_only=False, data_only=False)
    assert workbook.properties.title == "PHNER graph intake workbook"
    assert workbook.sheetnames == [
        "Instructions",
        "Entities",
        "Relationships",
        "Sources",
        "Names",
        "Locations",
        "Platform Participations",
        "Relationship Guide",
        "Lookup Values",
        "Examples",
    ]
