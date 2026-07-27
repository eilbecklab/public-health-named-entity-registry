# Strategy review

The implementation strategy is sound and appropriately conservative for a
high-governance registry. Its strongest choices are durable identity separated
from names, first-class evidence-backed relationships, one global namespace,
Git-reviewed YAML, and a rebuildable Neo4j projection.

The first draft resolves two internal gaps:

1. `SAME_AS` was required to carry explicit merge-review metadata, but no schema
   field was proposed. `IdentityReview` now supplies reviewer, date, and
   rationale only where exact identity is asserted.
2. Scanning current files cannot prevent ID reuse after deletion. A tracked,
   atomically updated reservation ledger is used in addition to collision scans.

The governance process and minimum approval roles are now documented, but the
role-assignment table remains intentionally unassigned. Before production
curation, the project still must approve or assign:

- the named people or groups holding each governance role;
- the durable schema and entity URI namespace replacing `example.org`;
- which classifications and relationship endpoint rules are approved;
- how stale a review may be and whether each warning blocks release;
- the release-ID sequence owner across concurrent branches;
- the legal license and contributor policy;
- the initial decision records approving `SAME_AS`, split, merger, retirement,
  and dispute procedures.

Recommended hardening after this draft:

- add migration tooling before the first breaking schema change;
- sign release checksums or provenance attestations;
- regenerate and byte-compare all views during independent verification;
- add field-level assertions only when real curation demonstrates the need;
- test against the deployed Neo4j version in an integration job;
- introduce a dependency lock after selecting the supported Python versions.

External geographic, organizational, and semantic cross-references remain
deferred. Their governance and proposed additive model are documented in the
[external cross-reference roadmap](roadmap/external-cross-references.md).
