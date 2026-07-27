# Deferred external cross-references

**Status:** Future design; not implemented in the MVP

External identifiers are not fields in the current LinkML schema, templates,
canonical data, or release outputs. This document preserves an additive design
path without authorizing cross-reference data to be added now.

## Why PHNER maintains its own identifiers

No existing identifier system covers PHNER's full range and granularity:

- legal organizations and organizational units;
- offices, divisions, laboratories, and facilities;
- programs, initiatives, networks, and working groups;
- technical platforms;
- jurisdictions and named geographic or reporting regions.

External systems serve narrower purposes and may identify a legal entity,
award recipient, tax account, physical establishment, research organization,
federal organization, or geographic concept at a different granularity.
External identifiers therefore supplement PHNER identity; they never replace
it.

Examples that may warrant later evaluation include:

- ROR identifiers for research organizations within ROR's scope;
- SAM.gov Unique Entity IDs for entities participating in United States federal
  award and registration processes;
- CAGE and NCAGE codes, which may be location-sensitive;
- EINs for United States federal tax administration, subject to sensitivity and
  redistribution review;
- SAM.gov Federal Hierarchy identifiers and agency codes;
- Treasury, accounting, budget, or awarding-organization codes;
- approved geographic and reporting code systems.

ORCID iDs identify people and are outside PHNER's current named-entity scope.
They should not be added unless PHNER governance separately approves modeling
people, privacy requirements, and authenticated collection.

## Proposed model

A future `CrossReference` should be a qualified record associated with an
existing PHNER entity. Its likely fields are:

```yaml
entity_id: phner-ent-000001
scheme:
value:
issuing_authority:
scheme_version:
record_uri:
match_type:
assertion_status:
valid_from:
valid_to:
source_ids: []
verified_at:
verified_by:
rationale:
```

The exact schema requires a separate approved decision and implementation
change. Do not add empty cross-reference arrays to current entity records.

## Separate semantic dimensions

Do not combine match semantics, temporal validity, and review state.

### Match type

Match direction is evaluated from the PHNER entity to the external record:

- `exact`: the PHNER entity and external record denote the same entity;
- `broader`: the external record denotes an entity broader than the PHNER
  entity;
- `narrower`: the external record denotes an entity narrower than the PHNER
  entity;
- `related`: the records are relevant to each other without identity or
  hierarchical equivalence;
- `uncertain`: available evidence does not establish the relationship.

Only `exact` expresses identity equivalence. It still does not replace the
PHNER identifier or create a PHNER `SAME_AS` relationship automatically.

### Temporal validity

Use `valid_from` and `valid_to` to describe when an identifier or mapping
applied. “Historical” is not a match type: a historical mapping may have been
exact, broader, narrower, related, or uncertain during its validity interval.

### Assertion status

Use the PHNER assertion statuses `verified`, `provisional`, `candidate`, and
`disputed` for review state. `illustrative` remains restricted to synthetic
tests and examples.

## Preferred mapping behavior

Attach an exact external identifier to the PHNER entity that actually denotes
the external record. If the external record identifies a parent legal entity,
award recipient, or physical establishment and PHNER represents that entity,
attach the exact mapping there and connect other PHNER entities with explicit
relationships such as `PART_OF`, `OPERATED_BY`, or `LOCATED_IN`.

A broader or narrower mapping may be useful when the corresponding entity is
not represented in PHNER and the integration use case requires the qualified
association. Its rationale must explain why an exact mapping to a separate
PHNER entity was not used.

## Required metadata and validation

An approved implementation should record and validate, as applicable:

- scheme name and normalized identifier value;
- issuing authority;
- scheme version, edition, or data vintage;
- record URI;
- case sensitivity, punctuation, and canonical formatting;
- supporting evidence and retrieval date;
- match type, rationale, and assertion status;
- validity dates;
- curator and verification date.

Exact mappings should be unique when the external scheme guarantees unique
identity. Multiple PHNER entities claiming the same exact external record must
produce a conflict for curator review, never an automatic merge.

## Restrictions

Curators and import tools must not:

- copy a parent organization's identifier onto subordinate units;
- assume identity because names or addresses are similar;
- treat shared funding, ownership, or administration as identity;
- merge PHNER entities solely because they share an external identifier;
- renumber a PHNER entity when an external identifier changes;
- overwrite conflicting or historical mappings silently;
- attach an identifier without its scheme and evidence;
- store credentials, authentication tokens, non-public identifiers, or
  sensitive values;
- publish data without confirming licensing and redistribution rights.

## Conflicts and changes

When sources disagree:

1. preserve the existing reviewed mapping;
2. add the conflicting evidence;
3. set the assertion status to `disputed` when appropriate;
4. open a governance decision when identity or canonical mapping would change;
5. preserve time-bounded historical mappings.

External identifiers may be deprecated, reassigned, reformatted, or replaced by
their issuing authorities. Such changes do not alter PHNER identity.

## Scheme approval checklist

Before implementation, the decision record must document:

- the registry or integration use case;
- issuing authority and covered entity types;
- geographic and jurisdictional scope;
- licensing, access, privacy, and redistribution terms;
- versioning, update, reassignment, and deprecation behavior;
- match semantics and direction;
- evidence and verification requirements;
- maintenance owner;
- normalization and validation rules;
- conflict and migration procedures;
- tests and documentation.

An identifier scheme should be adopted only for a defined requirement, not
merely because identifiers are available.

## Authoritative starting references

- [ORCID: What is an ORCID iD?](https://support.orcid.org/hc/en-us/articles/360006897334-What-is-an-ORCID-iD-and-how-do-I-use-it)
- [ROR scope and criteria](https://ror.org/registry/)
- [SAM.gov entity registration and Unique Entity ID](https://sam.gov/entity-registration)
- [FAR 52.204-16: CAGE and NCAGE definitions](https://www.acquisition.gov/far/52.204-16)
- [SAM.gov Federal Hierarchy Public API](https://open.gsa.gov/api/fh-public-api/)
- [IRS: Employer identification number](https://www.irs.gov/businesses/employer-identification-number)
- [Deferred geographic cross-references](geographic-cross-references.md)

