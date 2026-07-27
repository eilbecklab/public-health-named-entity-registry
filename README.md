# Public Health Named Entity Registry

PHNER is a Neo4j-first property graph of public-health named entities and their
relationships. Neo4j is the authoritative operational store. The files in this
repository define the graph contract, constraints, controlled relationship
types, validation, and interchange formats.

This repository contains an executable MVP. It does **not** contain production
entities.

## Quick start

Create the Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Configure a running Neo4j database:

```bash
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_DATABASE="neo4j"
read -rsp "Neo4j password: " NEO4J_PASSWORD
echo
export NEO4J_PASSWORD
```

Do not put the password in this repository or directly in a command.

Initialize and check the graph:

```bash
phner graph check
phner graph init
phner graph validate
phner graph stats
```

Create entity stubs with collision-safe PHNER IDs:

```bash
phner graph new-entity \
  --name "Example Public Health Organization" \
  --type organization \
  --created-by "$USER"
```

Create an identified relationship after both endpoint entities exist:

```bash
phner graph new-relationship \
  --subject phner-ent-000001 \
  --type OPERATES_IN \
  --object phner-ent-000002 \
  --created-by "$USER"
```

The commands print the assigned identifiers. Open the database in Neo4j Bloom
to edit properties and visually connect records. Use the CLI to allocate IDs
before editing so uniqueness does not depend on a person choosing a number.

See [the Neo4j workflow](docs/neo4j-workflow.md) and
[the curation guide](CURATION_GUIDE.md) for the complete workflow.

## Graph contract

The canonical graph uses:

- `NamedEntity` nodes with stable `entity_id` values;
- a secondary label such as `Organization`, `Jurisdiction`, or `Platform`;
- typed domain relationships such as `PART_OF` and `OPERATES_IN`;
- stable `relationship_id` properties on domain relationships;
- repository-controlled constraints and indexes in `neo4j/migrations/`;
- entity labels in `mappings/neo4j_mapping.yaml`;
- relationship vocabulary and endpoint rules in
  `mappings/relationship_rules.yaml`.

The LinkML schema remains useful as an interchange contract and artifact
generator. YAML under `data/` is optional import/export material, not the
authoritative editing surface.

## Validation, export, and backup

Run live graph validation:

```bash
phner graph validate
```

Create a portable JSON snapshot for inspection or downstream processing:

```bash
phner graph export
```

The default output is `build/neo4j-snapshot.json`, which is ignored by Git.
This snapshot is not an operational database backup. Use the backup facilities
appropriate to the deployed Neo4j edition and hosting model.

## Source-of-truth boundary

1. Neo4j contains canonical entities and relationships.
2. Git contains graph migrations, mapping rules, validation code, and docs.
3. Bloom is the initial human editing interface.
4. A future browser can use the official Neo4j driver or API against the same
   stable graph contract.
5. YAML, CSV, JSON, RDF, and release bundles are interchange or publication
   views, not parallel master copies.
