# Graph snapshot and backup guide

Neo4j is the canonical PHNER store. Publishing source code and graph-contract
migrations is separate from backing up or exporting graph data.

## Validate before a snapshot

```bash
phner graph check
phner graph validate
phner graph stats
```

Resolve validation errors before creating a snapshot intended for downstream
use.

## Portable snapshot

```bash
phner graph export --output build/neo4j-snapshot.json
```

The JSON snapshot contains PHNER nodes, labels, properties, and relationships
in stable business-key order. It is useful for:

- inspecting the graph outside Neo4j;
- automated tests and downstream transformations;
- publishing a deliberately reviewed data extract;
- rebuilding noncanonical search or analytics views.

It is not an operational backup and does not include database configuration,
users, roles, indexes, constraints, transaction history, or every Neo4j data
type.

## Operational backup

Use the method supported by the deployed Neo4j environment:

- Enterprise deployments: online `neo4j-admin database backup`;
- offline deployments: `neo4j-admin database dump`;
- Aura: the backup and snapshot facilities supplied by Aura.

Test restoration on a separate database. Store backups outside the source
repository with appropriate access controls and retention.

## Graph-contract release

Changes to labels, relationship types, constraints, or required properties
should include:

1. a new numbered file under `neo4j/migrations/` when database state changes;
2. matching updates to mappings and validation;
3. tests and documentation;
4. a successful disposable-database smoke test.

Never rewrite a migration already applied to a shared database. Add a new
migration that advances the existing state.

## Legacy interchange bundles

The older commands remain available for YAML-based interchange:

```bash
phner validate registry
phner release prepare --version 0.1.0
phner release verify build/
```

Those bundles are derived from YAML under `data/`; they do not export the
canonical Neo4j database and should not be presented as a graph backup.
