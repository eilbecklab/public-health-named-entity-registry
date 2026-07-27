from __future__ import annotations

import pytest

from public_health_named_entity_registry.release import ReleaseError, build_bundle, verify_release


def test_build_and_verify_synthetic_bundle(valid_project, tmp_path):
    output = tmp_path / "bundle"
    build_bundle(
        valid_project,
        output,
        version="0.1.0",
        status="candidate",
        release_id="phner-release-2026-001",
        release_policy=True,
        include_schema_artifacts=False,
    )
    verify_release(output, valid_project)
    assert (output / "neo4j" / "constraints.cypher").exists()
    assert "phner-ent-900001" in (output / "neo4j" / "import.cypher").read_text()


def test_verification_detects_tampering(valid_project, tmp_path):
    output = tmp_path / "bundle"
    build_bundle(
        valid_project,
        output,
        version="0.1.0",
        release_id="phner-release-2026-001",
        release_policy=True,
        include_schema_artifacts=False,
    )
    (output / "registry.json").write_text("{}\n")
    with pytest.raises(ReleaseError, match="Checksum mismatch"):
        verify_release(output, valid_project)


def test_verification_detects_unlisted_file(valid_project, tmp_path):
    output = tmp_path / "bundle"
    build_bundle(
        valid_project,
        output,
        version="0.1.0",
        release_id="phner-release-2026-001",
        release_policy=True,
        include_schema_artifacts=False,
    )
    (output / "unexpected.txt").write_text("not in checksums\n")
    with pytest.raises(ReleaseError, match="Unlisted release file"):
        verify_release(output, valid_project)


def test_build_is_reproducible_with_source_date_epoch(valid_project, tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1785168000")
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in [first, second]:
        build_bundle(
            valid_project,
            output,
            version="0.1.0",
            release_id="phner-release-2026-001",
            release_policy=True,
            include_schema_artifacts=False,
        )
    assert (first / "checksums.txt").read_bytes() == (second / "checksums.txt").read_bytes()


def test_build_refuses_unmarked_nonempty_destination(valid_project, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "user-file.txt").write_text("preserve me\n")
    with pytest.raises(ReleaseError, match="unmarked non-empty"):
        build_bundle(valid_project, output, include_schema_artifacts=False)
    assert (output / "user-file.txt").read_text() == "preserve me\n"
