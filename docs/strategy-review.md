# Neo4j-first strategy

PHNER now treats Neo4j as the canonical operational registry rather than as a
disposable projection of hand-edited YAML.

## Rationale

The intended downstream platform is Neo4j, named entities must be editable
independently, and a graph browser will be built on top of the result. Making
Neo4j canonical removes an unnecessary synchronization boundary and allows
Bloom to provide an immediate visual editing interface.

The parts of the original design that remain valuable are:

- stable opaque PHNER identifiers;
- controlled entity labels and relationship types;
- explicit relationship direction;
- validation independent of the editing interface;
- repository-reviewed schema migrations and mapping rules;
- portable exports and reproducible downstream transformations.

## MVP decisions

- Neo4j is the source of truth for canonical entities and relationships.
- Bloom is the interim human editor.
- The CLI atomically allocates entity and relationship IDs.
- Git stores migrations, validation, mappings, tests, and documentation.
- LinkML and YAML remain interchange mechanisms.
- `phner graph export` is a portable snapshot, not a database backup.
- Operational recovery uses Neo4j-native backup or dump facilities.

## Near-term work

1. Load a small representative set of provisional entities.
2. Refine node properties and relationship types through real graph queries.
3. Add evidence-source and platform-participation creation commands.
4. Add domain-specific Cypher validation for relationship endpoints and cycles.
5. Configure a shared Bloom Perspective.
6. Define backup, restore, and access-control procedures for the deployed
   Neo4j environment.
7. Build a thin browser directly against the stable graph contract.

Formal publication governance, external cross-reference policy, and advanced
release packaging can wait until the graph and browser workflow are proven.
