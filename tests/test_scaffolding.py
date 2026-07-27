from __future__ import annotations

import yaml

from public_health_named_entity_registry.identifiers import reserve_id
from public_health_named_entity_registry.scaffolding import new_record


def test_reservations_are_monotonic(empty_project):
    assert reserve_id("entity", empty_project) == "phner-ent-000001"
    assert reserve_id("entity", empty_project) == "phner-ent-000002"


def test_new_record_is_blank_and_never_overwrites(empty_project):
    first = new_record("entity", empty_project, name_slug="Synthetic Placeholder")
    second = new_record("entity", empty_project)
    first_data = yaml.safe_load(first.read_text())
    assert first.name == "phner-ent-000001--synthetic-placeholder.yaml"
    assert first_data["entity_id"] == "phner-ent-000001"
    assert first_data["preferred_name"] is None
    assert second.name == "phner-ent-000002.yaml"


def test_curator_supplied_value_is_copied_exactly(empty_project):
    path = new_record(
        "relationship",
        empty_project,
        supplied={"subject_entity_id": "phner-ent-001234"},
    )
    assert yaml.safe_load(path.read_text())["subject_entity_id"] == "phner-ent-001234"
