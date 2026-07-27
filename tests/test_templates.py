from __future__ import annotations

import yaml

from public_health_named_entity_registry.config import RECORD_CONFIG
from public_health_named_entity_registry.loader import load_record
from public_health_named_entity_registry.schema_validation import SchemaValidator


def test_template_fields_match_linkml_classes(repository_root):
    validator = SchemaValidator(repository_root)
    for record_type, config in RECORD_CONFIG.items():
        path = repository_root / "templates" / config["template"]
        data = yaml.safe_load(path.read_text())
        expected = set(validator.classes[config["class"]]["attributes"])
        assert set(data) == expected, record_type


def test_untouched_entity_template_fails_validation(repository_root, tmp_path):
    path = tmp_path / "data" / "entities" / "template.yaml"
    path.parent.mkdir(parents=True)
    path.write_text((repository_root / "templates" / "entity.yaml").read_text())
    record, loader_issues = load_record(path, "entity")
    assert record is not None
    issues = [*loader_issues, *SchemaValidator(repository_root).validate_record(record)]
    assert any(issue.code == "required-field" for issue in issues)
