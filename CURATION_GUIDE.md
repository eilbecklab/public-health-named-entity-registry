# Curation guide

PHNER records are curated directly in Neo4j. The CLI creates stable identifiers
and baseline records; Neo4j Bloom is the initial visual editor.

## 1. Initialize a database

Configure the `NEO4J_*` environment variables described in
[`docs/neo4j-workflow.md`](docs/neo4j-workflow.md), then run:

```bash
phner graph check
phner graph init
```

## 2. Create a named entity

```bash
phner graph new-entity \
  --name "Working display name" \
  --type organization \
  --created-by "$USER"
```

The printed `phner-ent-NNNNNN` identifier is permanent. Do not replace it with
a Neo4j internal element ID, an external organization code, or a name-derived
identifier.

Open the entity in Bloom and complete the useful properties. Keep
`assertion_status` as `provisional` while the graph is exploratory.

## 3. Create a relationship

```bash
phner graph new-relationship \
  --subject phner-ent-000001 \
  --type OPERATES_IN \
  --object phner-ent-000002 \
  --created-by "$USER"
```

Relationship direction is significant. Consult
[`mappings/relationship_rules.yaml`](mappings/relationship_rules.yaml) before
choosing the type. Add `valid_from`, `valid_to`, and `source_ids` properties in
Bloom when they are known.

## 4. Validate frequently

```bash
phner graph validate
phner graph stats
```

Validation is especially important after direct Bloom edits because Bloom
provides general graph editing rather than PHNER-specific forms.

## 5. Work safely

- Allocate new IDs through the CLI.
- Treat `entity_id` and `relationship_id` as immutable.
- Do not use Neo4j internal element IDs as external identifiers.
- Avoid deleting entities during exploration; mark their status instead.
- Do not commit credentials, graph exports, or database backups.
- Back up the database using the method appropriate to the Neo4j deployment.

## Optional YAML interchange

The older `phner new`, `phner validate registry`, and `phner build` commands
remain available for structured interchange and migration work. YAML files in
`data/` are not synchronized automatically with Neo4j and are not canonical in
the Neo4j-first workflow.
