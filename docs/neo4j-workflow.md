# Neo4j workflow

The Excel workbook is the drafting and intake surface. Neo4j becomes the PHNER
source of truth after reviewed records are imported. This document describes
the current database operations before a workbook importer or dedicated browser
is available.

## 1. Connect

Set connection details in the shell:

```bash
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_DATABASE="neo4j"
read -rsp "Neo4j password: " NEO4J_PASSWORD
echo
export NEO4J_PASSWORD
```

For Neo4j Aura, use the provided `neo4j+s://` URI. Never commit a password or
put it directly on a command line.

Verify the connection:

```bash
phner graph check
```

## 2. Initialize the graph contract

```bash
phner graph init
```

This applies each ordered file in `neo4j/migrations/` once and records it as a
`PhnerMigration` node. The first migration creates uniqueness constraints and
lookup indexes.

Migrations should be additive and idempotent where practical. Never edit a
migration that has already been applied to a shared database; add a new
numbered migration.

## 3. Workbook boundary

The workbook is not synchronized automatically with Neo4j. Continue gathering
and reviewing records there until an import command is available. Temporary
workbook keys must not be copied into Neo4j as permanent identifiers.

The commands below support individual records and smoke testing in the
meantime.

## 4. Create and edit individual entities

Create a stub:

```bash
phner graph new-entity \
  --name "Example Organization" \
  --type organization \
  --created-by "$USER"
```

The command atomically allocates an ID and creates a node similar to:

```cypher
(:NamedEntity:Organization {
  entity_id: "phner-ent-000001",
  entity_type: "organization",
  preferred_name: "Example Organization",
  status: "active",
  assertion_status: "provisional"
})
```

Open Neo4j Bloom, generate a Perspective for the database, locate the entity by
`entity_id`, and edit its visible properties. Configure the Perspective so
`entity_id` and `preferred_name` are visible. Treat `entity_id` as immutable.

Bloom can create nodes directly, but the CLI is preferred because it assigns a
collision-safe ID. If Bloom is used to create a node, run `phner graph
validate` immediately and repair any missing required properties.

## 5. Create individual relationships

After both endpoint nodes exist:

```bash
phner graph new-relationship \
  --subject phner-ent-000001 \
  --type PART_OF \
  --object phner-ent-000002 \
  --created-by "$USER"
```

The allowed types come from `mappings/relationship_rules.yaml`. The CLI creates
a direct property-graph relationship carrying a stable `relationship_id`.
Additional properties such as `valid_from`, `valid_to`, `source_ids`, and
`assertion_status` can be edited in Bloom.

## 6. Validate

```bash
phner graph validate
phner graph stats
```

Current validation detects:

- missing, malformed, or duplicate PHNER IDs;
- blank entity names;
- entity types outside the graph contract;
- domain relationships without IDs;
- domain relationships with non-entity endpoints;
- relationship types outside the controlled vocabulary.

More domain checks can be added as Cypher-backed validators without moving
canonical data out of Neo4j.

## 7. Export and back up

Create a portable snapshot:

```bash
phner graph export
```

This writes `build/neo4j-snapshot.json`. It is useful for review, testing, and
building future transformations, but it is not a complete Neo4j backup.

Use Neo4j's database backup facilities for disaster recovery:

- Enterprise deployments can use online `neo4j-admin database backup`;
- offline deployments can use `neo4j-admin database dump`;
- Aura deployments should use the backup and snapshot features provided by
  Aura.

Keep production exports and database backups outside Git.

## 8. Future import

The first import command should validate workbook structure and controlled
values, report all errors before writing, allocate permanent IDs atomically,
and load a reviewed workbook in a transaction.

## Neo4j references

- [Neo4j Bloom graph editing](https://neo4j.com/docs/bloom-user-guide/current/bloom-tutorial/edit-graph-data/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Neo4j backup and restore](https://neo4j.com/docs/operations-manual/current/backup-restore/)
