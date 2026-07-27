from __future__ import annotations

import copy

from public_health_named_entity_registry.duplicate_detection import find_duplicates
from public_health_named_entity_registry.loader import load_registry
from public_health_named_entity_registry.models import Record


def test_duplicate_detection_is_read_only(valid_project):
    registry = load_registry(valid_project)
    original_count = len(registry.records)
    source = registry.records_of_type("entity")[0]
    duplicate_data = copy.deepcopy(source.data)
    duplicate_data["entity_id"] = "phner-ent-900099"
    registry.records.append(
        Record("entity", "NamedEntity", "phner-ent-900099", duplicate_data, source.path)
    )
    candidates = find_duplicates(registry)
    assert any(candidate.score == 1.0 for candidate in candidates)
    assert len(registry.records) == original_count + 1
