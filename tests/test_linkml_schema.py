from __future__ import annotations

import re

from public_health_named_entity_registry.schema_validation import SchemaValidator


def test_schema_defines_expected_primary_classes(repository_root):
    validator = SchemaValidator(repository_root)
    assert {
        "Registry",
        "NamedEntity",
        "EntityRelationship",
        "PlatformParticipation",
        "EvidenceSource",
    } <= set(validator.classes)


def test_identifier_patterns_are_namespaced(repository_root):
    validator = SchemaValidator(repository_root)
    patterns = {name: definition["pattern"] for name, definition in validator.types.items()}
    assert re.fullmatch(patterns["entity_identifier"], "phner-ent-000001")
    assert not re.fullmatch(patterns["entity_identifier"], "phner-rel-000001")
    assert re.fullmatch(patterns["release_identifier"], "phner-release-2026-001")
