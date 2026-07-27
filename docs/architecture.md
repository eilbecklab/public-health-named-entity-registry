# Architecture

PHNER separates four concerns:

```text
LinkML schema -> curator YAML -> validated release bundle -> CSV / Neo4j views
      |                |                   |
   structure       curated facts      immutable evidence
```

The LinkML schema is the only hand-maintained structural model. Python reads its
classes, slots, enums, and identifier types for record validation, then adds
cross-record rules that LinkML alone does not express: reference resolution,
relationship endpoint policies, cycles, temporal intervals, evidence coverage,
duplicate candidates, and release policy.

The loader reads only the four canonical directories. It never reads
`data/candidates`, tests, examples, releases, or generated build output.

Neo4j is an idempotent projection keyed only by PHNER IDs. It is not an editing
surface for registry-managed identity or naming fields.

Schema, identity, relationship-vocabulary, release-policy, and downstream
breaking changes follow [`GOVERNANCE.md`](../GOVERNANCE.md) and the
[decision-record workflow](decisions/README.md).
