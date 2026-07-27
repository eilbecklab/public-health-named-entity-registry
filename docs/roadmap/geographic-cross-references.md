# Deferred geographic cross-references

**Status:** Future design; not implemented in the MVP

The MVP assigns PHNER entity IDs to jurisdictions and named regions and does
not require external codes.

A later additive `CrossReference` model may carry PHNER entity ID, scheme,
value, scheme version, record URI, validity dates, source IDs, match type, and
curator status. Before adopting a scheme, document its use case, authority,
levels, update behavior, historical and disputed-area treatment, match
semantics, migration procedure, and maintenance owner.

External identifiers must never replace PHNER IDs or become Neo4j merge keys.

Geographic mappings must follow the general qualification, evidence, licensing,
match-direction, conflict, and scheme-approval rules in
[the external cross-reference roadmap](external-cross-references.md).
