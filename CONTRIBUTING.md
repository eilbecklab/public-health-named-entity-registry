# Contributing

Keep each curation change small and reviewable. Create canonical records through
`phner new`, cite curator-reviewed evidence, run registry validation and
duplicate detection, and inspect the Git diff.

Do not add scraped production records, inferred relationships, real entities in
test fixtures, generated `build/` files, external identifier placeholders, or
direct Neo4j state. Schema and vocabulary changes require tests and a migration
note when existing records are affected.

Routine curation may proceed under approved policy. Create a
[governance decision record](docs/decisions/README.md) when a change involves:

- `SAME_AS`, a merge, split, retirement, or rename-versus-replacement decision;
- a new or changed relationship or controlled-vocabulary value;
- registry scope, schema, validation, or release-policy changes;
- disputed-assertion resolution;
- external identifier schemes;
- breaking downstream or Neo4j projection changes.

The decision record, required reviewers, tests, migration, and affected
documentation should normally be reviewed in the same pull request. If one
person acts in multiple required roles, disclose that in the record.

Before production curation begins, the role-assignment table in
[`GOVERNANCE.md`](GOVERNANCE.md) must name the responsible people or groups.

The pull request template contains the curation and governance checklist.
