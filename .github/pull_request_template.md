## Summary

Describe the graph-contract, migration, validation, or tooling change.

## Governance

- Governed decision required: yes / no
- Decision record: link or not applicable
- Required reviewers: roles and names
- Migration or downstream impact: description or none

## Checklist

- [ ] Applied database changes use a new numbered Cypher migration
- [ ] Existing applied migrations were not rewritten
- [ ] PHNER business IDs remain stable and unique
- [ ] Entity labels and relationship types match the graph contract
- [ ] Live graph validation was run against a disposable database when applicable
- [ ] Unit tests, Ruff, and mypy pass
- [ ] No production graph export, dump, or credential was committed
- [ ] Governed changes have a decision record and required approvals
- [ ] Breaking changes include migration and downstream compatibility notes
