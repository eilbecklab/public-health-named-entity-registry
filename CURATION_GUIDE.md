# Curation guide

## 1. Create evidence first

Run `phner new source`, open the printed file, and transcribe only facts from a
curator-reviewed source. Give the source a type, title, and either a URL or
document identifier. Record retrieval date and a useful locator when possible.

## 2. Create a named entity

Run:

```bash
phner new entity --name-slug working-label --created-by "your curator ID"
```

The slug is only a filename aid. It is not identity and can change. Fill every
required field, attach one or more `source_ids`, and keep
`assertion_status: provisional` until the actual review is complete.

Use one of the small structural `entity_type` values. Use classifications for
specific categories. Administrative parentage, jurisdiction served, and
physical location are separate assertions.

See the [assertion status policy](GOVERNANCE.md#assertion-status-policy) before
changing a record to `verified`, `disputed`, or another review state.

## 3. Add relationships and participations

```bash
phner new relationship --subject phner-ent-000001 --object phner-ent-000002
phner new participation --entity phner-ent-000001 --platform phner-ent-000003
```

These flags copy values supplied by the curator; they do not infer facts.
Relationships require evidence. `SAME_AS` additionally requires
`identity_review` with reviewer, date, and rationale plus an approved
[governance decision record](docs/decisions/README.md).

## 4. Validate and review

```bash
phner validate file data/entities/phner-ent-000001.yaml
phner validate registry
phner find-duplicates
phner review record phner-ent-000001
phner review changed
```

Duplicate output is a warning list only. Never merge or retire identities
without an explicit governance decision.

## History decisions

Keep the same entity ID for a rename or ordinary detail change. Create a new
entity for a split, merger, replacement, or broken organizational continuity,
then add `SUCCESSOR_OF` or `PREDECESSOR_OF`.

A merge, split, retirement, `SAME_AS`, or rename-versus-replacement decision
requires the reviews defined in
[the governance approval matrix](GOVERNANCE.md#minimum-approval-matrix).
Create and approve the decision record before treating the identity change as
canonical.

A missing validity date means unknown. It does not assert infinite validity.

When evidence conflicts, preserve the existing reviewed assertion and both
sources, use `disputed` when the canonical claim is contested, and open a
decision record if resolving the conflict changes identity or policy.

## External identifiers

External cross-references are not implemented in the MVP. Do not add external
identifier fields, placeholder arrays, or identifiers to canonical records.
The future policy and design are documented in the
[external cross-reference roadmap](docs/roadmap/external-cross-references.md).

## Identifier collisions

The tracked `.phner/id-reservations.yaml` ledger prevents local reuse. Parallel
branches can reserve the same number, so merge the ledger carefully. If two
branches collide, keep the ID already merged to the target branch and run
`phner new ...` again on the other branch. Do not hand-edit an accepted ID.

If `.phner/id-reservations.lock` remains after an interrupted command, confirm
that no `phner` process is running before deleting only that lock file.
