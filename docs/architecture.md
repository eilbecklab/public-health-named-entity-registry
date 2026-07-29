# Architecture

PHNER is intentionally organized around one simple path:

```text
Excel intake workbook
        |
        | review and future import command
        v
canonical Neo4j graph
        |
        +-- Neo4j Bloom for graph inspection and editing
        +-- portable exports and database backups
```

## Excel intake

The workbook is optimized for research and data entry. Temporary keys connect
rows across sheets without asking an editor to allocate permanent identifiers.
Dropdown values and relationship rules come from the YAML mappings in this
repository.

The workbook is not a second graph database and is not synchronized with
Neo4j. A future import command should validate a reviewed workbook, allocate
permanent identifiers atomically, and load all accepted rows in a transaction.

## Neo4j

Neo4j is authoritative after import. Each `NamedEntity` receives a stable
`entity_id`, and each domain relationship receives a stable
`relationship_id`. These identifiers are opaque and must not encode names or
organizational structure.

The CLI applies database migrations, allocates identifiers, creates individual
entities and relationships, validates the live graph, reports counts, and
creates portable JSON snapshots.

Git stores only the reusable graph contract and tooling:

- controlled workbook values;
- entity-label and relationship mappings;
- Cypher constraints and indexes;
- workbook generation and Neo4j commands;
- tests and concise operating documentation.

Credentials, completed production workbooks, graph exports, and database
backups require separate handling appropriate to their sensitivity.
