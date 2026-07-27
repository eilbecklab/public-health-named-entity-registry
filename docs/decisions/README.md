# Governance decision records

This directory contains durable records for decisions governed by
[`GOVERNANCE.md`](../../GOVERNANCE.md).

## When a record is required

Create a decision record for:

- schema, controlled-vocabulary, or scope changes;
- new or materially changed relationship types;
- `SAME_AS`, merge, split, rename-versus-replacement, and retirement decisions;
- disputed-assertion resolutions;
- external identifier schemes;
- release-policy or downstream-breaking changes;
- release approval.

Routine curation that follows an already approved policy does not need a
separate decision record. Its evidence and review metadata remain in the
canonical record and pull request.

## File naming and lifecycle

Copy [`0000-template.md`](0000-template.md) to the next zero-padded number:

```text
0001-approve-initial-relationship-vocabulary.md
0002-decide-example-entity-continuity.md
```

Use one of these statuses:

- `proposed`
- `approved`
- `rejected`
- `superseded`

Do not reuse decision numbers. Proposed records may be edited during review.
Once approved or rejected, preserve the record. A later change creates a new
decision record whose `Supersedes` field points to the earlier record.

## Review

The record must name the proposer and the reviewers required by the governance
approval matrix. If one person acted in multiple roles or independent review
was unavailable, document that limitation.

The pull request approving the decision should contain the record and any
immediately required schema, documentation, migration, test, or canonical-data
changes. Deferred follow-up must have an owner and tracking reference.

