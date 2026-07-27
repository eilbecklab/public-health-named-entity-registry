# Governance

**Status:** Draft  
**Effective date:** Not yet approved  
**Applies to:** PHNER schema, canonical records, controlled vocabularies,
validation policy, releases, and downstream projections

No production curation or public release should begin until the required roles,
initial controlled vocabularies, relationship rules, and release policy have
been approved.

## MVP boundary

The MVP supports PHNER identifiers, named entities, relationships, platform
participations, evidence, and releases.

External cross-references are governed here as a future capability but are not
part of the current LinkML schema, templates, canonical data, validation path,
or release pipeline. Do not add external-identifier fields or placeholder
values to canonical records until an additive schema change has been approved.
See [the external cross-reference roadmap](docs/roadmap/external-cross-references.md).

## Roles and assignments

The registry must designate named people or groups for the following roles:

- **Registry steward:** accountable for registry policy, disputes, scope, and
  release approval.
- **Domain curator:** responsible for verifying entity identity, names,
  classifications, relationships, evidence, and assertion status.
- **Schema maintainer:** responsible for the LinkML schema, controlled
  vocabularies, migrations, and schema-version policy.
- **Technical maintainer:** responsible for validation, generation, tests, CI,
  release tooling, and reproducible builds.
- **Integration owner:** responsible for Neo4j projections, downstream data
  contracts, and source-of-truth boundaries.

One person or group may hold more than one role, but responsibility for each
role must be documented. When one person acts in multiple required roles, the
decision record must disclose that fact.

| Role | Assigned person or group | Contact | Effective date | Backup |
|---|---|---|---|---|
| Registry steward | Unassigned | — | — | — |
| Domain curator | Unassigned | — | — | — |
| Schema maintainer | Unassigned | — | — | — |
| Technical maintainer | Unassigned | — | — | — |
| Integration owner | Unassigned | — | — | — |

Add repository `CODEOWNERS` only after these assignments and repository
identities are known.

## Governed decisions

The following decisions require a record under
[`docs/decisions/`](docs/decisions/README.md):

- schema and controlled-vocabulary changes;
- registry scope changes;
- new or materially changed relationship types;
- `SAME_AS` assertions and reversals;
- duplicate merges and identity splits;
- rename-versus-replacement decisions;
- successor and predecessor decisions;
- record retirement after publication;
- geographic and jurisdiction policy;
- external identifier schemes and mapping policy;
- changes to assertion-status or release criteria;
- changes affecting downstream projections or compatibility.

A `verified` assertion status is a curator decision. Automation may validate,
report warnings, and suggest possible duplicates, but it must never assign
`verified`, merge entities, retire identifiers, or infer canonical identity.

### Minimum approval matrix

| Decision | Required review |
|---|---|
| Routine record verification | Domain curator |
| `SAME_AS`, merge, split, or rename-versus-replacement | Domain curator and registry steward |
| New relationship or controlled-vocabulary value | Schema maintainer and registry steward |
| Breaking schema or projection change | Schema maintainer, technical maintainer, integration owner, and registry steward |
| Disputed assertion resolution | Domain curator and registry steward |
| External identifier scheme | Schema maintainer, integration owner, and registry steward |
| Release approval | Registry steward after technical validation |

For identity-changing and release decisions, a reviewer other than the proposer
is preferred. If staffing makes independent review impossible, record that
limitation and the compensating review performed.

### Decision records

Decision records must identify:

- the decision and status;
- the date;
- the proposer and required reviewers;
- the evidence considered;
- the rationale and alternatives;
- affected records, schema elements, or integrations;
- compatibility and release impact;
- required migration or follow-up action.

Approved decision records are append-only. Supersede an earlier decision with a
new record rather than silently rewriting its outcome.

## Assertion status policy

Assertion status describes review state, not numeric confidence.

| Status | Meaning | Permitted in a release |
|---|---|---|
| `verified` | A domain curator completed the required review | Yes |
| `provisional` | Canonical work in progress with evidence, not fully reviewed | Yes, clearly labeled |
| `candidate` | Proposed assertion not accepted as release-ready canonical data | No |
| `disputed` | Conflicting evidence or interpretation is intentionally preserved | Yes, with evidence and curator notes |
| `illustrative` | Synthetic or explanatory content | No; tests and examples only |

Changing an assertion to `verified` requires a named curator and review date.
Changing a disputed assertion requires preserving the conflicting evidence and
documenting the resolution. Release tooling must reject `candidate` and
`illustrative` assertions.

## PHNER identifier policy

Every canonical record receives the PHNER identifier type defined for that
record:

- named entity: `phner-ent-NNNNNN`;
- relationship: `phner-rel-NNNNNN`;
- platform participation: `phner-par-NNNNNN`;
- evidence source: `phner-src-NNNNNN`;
- release: `phner-release-YYYY-NNN`.

Entity identifiers are the stable, authoritative identity keys used for entity
references and downstream Neo4j merges. Relationship, participation, evidence,
and release IDs identify their respective records.

PHNER identifiers are opaque. They must not encode a record's name, type,
country, jurisdiction, organizational position, or external identifier.

A PHNER identifier must:

- remain stable when names, aliases, URLs, classifications, or mappings change;
- never be reassigned to another record;
- never be reused after reservation, even when an unpublished draft is
  abandoned;
- remain represented in canonical history after publication;
- be replaced by a new entity ID when an approved decision determines that a
  split, merger, replacement, or break in continuity created a genuinely new
  entity.

Published entities must not disappear silently from later releases. Retain
retired, superseded, inactive, or dissolved entities as canonical records with
appropriate status, dates, evidence, and historical relationships. A future
release-to-release check should enforce this retention rule automatically.

## External cross-reference policy

PHNER maintains its own identifiers because no external system covers the full
range and granularity of entities represented by the registry. External
identifiers must never replace PHNER IDs, determine PHNER identity, or become
Neo4j merge keys.

An external identifier scheme may be implemented only after governance approves:

- a documented use case and maintenance owner;
- issuing authority, scope, and entity granularity;
- licensing, redistribution, privacy, and sensitivity constraints;
- versioning, update, reassignment, and deprecation behavior;
- match direction and semantics;
- evidence and curator-review requirements;
- normalization and validation rules;
- conflict, migration, and removal procedures;
- tests and documentation.

Cross-references must be qualified and evidence-backed. Curators must not infer
identity from similar names, shared addresses, funding, ownership,
administration, or a shared external identifier. Two PHNER entities claiming an
exact match to the same external record require conflict review; they must
never be merged automatically.

Only identifiers that may lawfully and appropriately be stored and redistributed
may enter a public registry release. Do not store credentials, authentication
tokens, non-public identifiers, or sensitive values.

Detailed proposed semantics and system examples are intentionally deferred to
[the external cross-reference roadmap](docs/roadmap/external-cross-references.md).

## Conflicts, appeals, and superseding decisions

When sources or reviewers disagree:

1. preserve the existing reviewed assertion and its evidence;
2. add the conflicting evidence without silently overwriting history;
3. mark the assertion `disputed` when the conflict affects the canonical claim;
4. open a decision record identifying the competing interpretations;
5. obtain the reviews required by the approval matrix;
6. preserve historical values when they were valid during an earlier period.

The registry steward resolves procedural disputes and confirms that the required
review occurred. A materially new fact or interpretation may reopen a decision.
The new decision record must link to and explicitly supersede the earlier one.

## Release governance

A release candidate is not an approved release. Before tagging or publishing,
the registry steward must confirm in a decision record that:

- required validation and release verification passed;
- warnings and duplicate candidates were reviewed;
- governed changes have approved decision records;
- migrations and downstream compatibility were addressed;
- the release contains no candidate or illustrative assertions;
- publication and licensing requirements are satisfied.

Release preparation, approval, tagging, and publication remain separate
actions. Validation and release tooling must never publish automatically.
