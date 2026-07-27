from __future__ import annotations

import shutil

import yaml

from public_health_named_entity_registry.validation import has_errors, validate_registry


def test_empty_registry_is_valid(empty_project):
    _registry, issues = validate_registry(empty_project)
    assert not has_errors(issues)


def test_valid_synthetic_registry_passes(valid_project):
    _registry, issues = validate_registry(valid_project, release=True)
    assert not has_errors(issues), [issue.as_dict() for issue in issues]


def test_missing_reference_fails(valid_project):
    path = valid_project / "data" / "relationships" / "phner-rel-900001.yaml"
    data = yaml.safe_load(path.read_text())
    data["object_entity_id"] = "phner-ent-999999"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    _registry, issues = validate_registry(valid_project)
    assert any(issue.code == "missing-object" for issue in issues)


def test_part_of_cycle_fails(valid_project):
    source = valid_project / "data" / "relationships" / "phner-rel-900001.yaml"
    data = yaml.safe_load(source.read_text())
    data["relationship_id"] = "phner-rel-900002"
    data["subject_entity_id"] = "phner-ent-900001"
    data["object_entity_id"] = "phner-ent-900002"
    target = source.with_name("phner-rel-900002.yaml")
    target.write_text(yaml.safe_dump(data, sort_keys=False))
    _registry, issues = validate_registry(valid_project)
    assert any(issue.code == "relationship-cycle" for issue in issues)


def test_candidates_are_excluded_from_loader(valid_project):
    source = valid_project / "data" / "entities" / "phner-ent-900001.yaml"
    candidate = valid_project / "data" / "candidates" / "candidate.yaml"
    shutil.copy2(source, candidate)
    registry, _issues = validate_registry(valid_project)
    assert len(registry.records_of_type("entity")) == 3


def test_inverse_relationship_in_same_direction_fails(valid_project):
    directory = valid_project / "data" / "relationships"
    template = yaml.safe_load((directory / "phner-rel-900001.yaml").read_text())
    template["subject_entity_id"] = "phner-ent-900001"
    template["object_entity_id"] = "phner-ent-900002"
    for identifier, relationship_type in [
        ("phner-rel-900010", "SUCCESSOR_OF"),
        ("phner-rel-900011", "PREDECESSOR_OF"),
    ]:
        record = dict(template)
        record["relationship_id"] = identifier
        record["relationship_type"] = relationship_type
        (directory / f"{identifier}.yaml").write_text(yaml.safe_dump(record, sort_keys=False))
    _registry, issues = validate_registry(valid_project)
    assert any(issue.code == "inverse-direction-contradiction" for issue in issues)


def test_verified_assertion_requires_reviewer_and_date(valid_project):
    path = valid_project / "data" / "entities" / "phner-ent-900001.yaml"
    data = yaml.safe_load(path.read_text())
    data["curation"]["reviewed_by"] = None
    data["curation"]["last_reviewed"] = None
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    _registry, issues = validate_registry(valid_project)
    codes = {issue.code for issue in issues}
    assert "verified-without-reviewer" in codes
    assert "verified-without-review-date" in codes


def test_disputed_assertion_requires_notes(valid_project):
    path = valid_project / "data" / "entities" / "phner-ent-900001.yaml"
    data = yaml.safe_load(path.read_text())
    data["curation"]["assertion_status"] = "disputed"
    data["curation"]["notes"] = None
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    _registry, issues = validate_registry(valid_project)
    assert any(issue.code == "disputed-without-notes" for issue in issues)
