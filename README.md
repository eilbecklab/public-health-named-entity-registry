# Public Health Named Entity Registry

PHNER is a small Excel-to-Neo4j project for gathering public-health named
entities and turning reviewed records into a property graph.

The immediate workflow is:

```text
Excel intake workbook → review and validation → Neo4j import → graph editing
```

The spreadsheet is the convenient drafting surface. Neo4j becomes the
authoritative store after data is imported.

## Start gathering information

Open the versioned
[working federal DHHS intake workbook](intake/US-FED-DHHS.xlsx) and begin with:

1. **Entities** — one row per organization or organizational unit. Use
   `parent_intake_key` to record the internal hierarchy.
2. Use the calculated `breadcrumb` column to review each entity's complete
   hierarchy path.
3. **Names** — optional aliases and other names.
4. **Relationships** — optional directed connections not represented by the
   internal parent hierarchy.

See the
[workbook guide](docs/intake-workbook.md), [evidence guide](docs/evidence-guide.md),
and [relationship guide](docs/relationship-guide.md) for field guidance.

Use temporary workbook keys such as `ENT-001` and `REL-001`. Do not assign
permanent `phner-*` identifiers manually.

The working workbook is committed to this public repository. Do not enter
private, confidential, or restricted information in it. The unchanged
[blank template](templates/phner-intake-template.xlsx) remains available when
you need a fresh workbook.

The repository does not yet contain the Excel import command. Until it is
implemented, treat a completed workbook as reviewed intake material rather
than as a synchronized copy of Neo4j.

## Install the tools

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Regenerate the blank template after changing the working workbook's columns,
formatting, validation, or reference tabs:

```bash
python scripts/generate_intake_workbook.py
```

## Connect Neo4j

Create and start a local Neo4j instance, then configure the terminal:

```bash
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_DATABASE="neo4j"
read -rsp "Neo4j password: " NEO4J_PASSWORD
echo
export NEO4J_PASSWORD
```

Initialize and verify the database:

```bash
phner graph check
phner graph init
phner graph validate
phner graph stats
```

The CLI can also create individual entities and relationships directly. See
the [Neo4j workflow](docs/neo4j-workflow.md).

## Relevant repository areas

- `intake/US-FED-DHHS.xlsx` — the versioned federal DHHS workbook
- `intake/US-UT-UDHHS.xlsx` — the versioned Utah DHHS workbook
- `templates/phner-intake-template.xlsx` — an unchanged blank starting point
- `scripts/generate_intake_workbook.py` — blank copy of the current workbook
- `mappings/controlled_values.yaml` — workbook dropdown values
- `mappings/neo4j_mapping.yaml` — entity type to Neo4j label mapping
- `mappings/relationship_rules.yaml` — allowed graph relationships
- `neo4j/migrations/` — database constraints and indexes
- `src/public_health_named_entity_registry/` — the small Neo4j CLI
- `tests/` — workbook and graph-contract checks

Do not commit passwords, database backups, or graph exports containing
production data.
