# Release guide

## Prepare

Commit the intended source records, then run:

```bash
phner validate registry --release-policy
phner release prepare --version 0.1.0
```

Preparation normally requires a clean Git worktree. `--allow-dirty` is an
explicit acknowledgement for local experiments and should not be used for an
approved release.

The candidate bundle contains assembled YAML and JSON, CSV tables, LinkML
JSON Schema and Python models, generated schema documentation, Neo4j Cypher,
quality and review reports, release notes, a manifest, and SHA-256 checksums.

Release preparation rejects structural errors, unresolved references, missing
evidence, graph-policy errors, and candidate or illustrative assertions.
It permits verified, provisional, and disputed assertions under the
[governance status policy](GOVERNANCE.md#assertion-status-policy). Warnings
still require curator review.

For reproducible timestamps in controlled builds, set `SOURCE_DATE_EPOCH`.

## Verify

```bash
phner release verify build/
```

Verification checks every listed digest and revalidates the assembled registry.
Any missing, changed, or structurally invalid artifact fails verification.

## Approve and publish

Inspect `build/review-report.md`, `build/quality-report.json`,
`build/release-manifest.yaml`, and `build/RELEASE_NOTES.md`.

The release pull request must include a decision record based on
[`docs/decisions/0000-template.md`](docs/decisions/0000-template.md). It should
identify the version, governed changes, validation result, reviewed warnings,
migrations, and downstream compatibility. The registry steward approves the
release only after technical validation and the required governed decisions are
approved.

A practical sequence is:

1. add the proposed release decision to the release pull request;
2. run validation, preparation, and verification in CI;
3. resolve warnings and obtain required reviews;
4. merge the approved source and decision record;
5. prepare and verify the bundle from the clean approved commit;
6. confirm the manifest Git commit and release ID;
7. create the annotated tag and publish explicitly.

Publication remains an explicit curator operation:

```bash
git add .
git commit -m "Release PHNER v0.1.0"
git tag -a v0.1.0 -m "PHNER v0.1.0"
git push origin main --follow-tags
```

The tooling never tags, pushes, creates a GitHub release, or writes to Neo4j.
