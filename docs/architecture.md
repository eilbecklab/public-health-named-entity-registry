# Architecture

PHNER uses Neo4j as its canonical operational store:

```text
Git-controlled graph contract
  ├── Cypher migrations and constraints
  ├── entity labels and relationship rules
  └── validation and interchange schema
                    |
                    v
             canonical Neo4j graph
              /        |         \
          Bloom     future UI     exports/backups
          editor     and APIs     for interchange
```

## Responsibilities

Neo4j stores the current named entities, their stable PHNER IDs, typed
relationships, and operational curation properties. Editors create an
ID-bearing entity stub through `phner graph new-entity`, then edit it in Bloom
or a future browser.

Git stores the contract for that graph:

- `neo4j/migrations/` contains ordered Cypher migrations;
- `mappings/neo4j_mapping.yaml` maps entity types to Neo4j labels;
- `mappings/relationship_rules.yaml` defines the allowed domain relationships;
- the LinkML schema defines interchange structures and enumerations;
- Python validation checks the live graph for contract violations.

## Identity

`entity_id` is the stable business key for every `NamedEntity`. Neo4j internal
element IDs must never be exposed as registry identifiers because they are not
portable across exports, restores, or database copies.

The CLI allocates identifiers atomically through `PhnerCounter` nodes. This
avoids collisions between concurrent editors. Domain relationships receive
their own `relationship_id` values for the same reason.

## Editing

Bloom is the initial editor. It can update visible node and relationship
properties and create connections directly in Neo4j. The PHNER CLI remains the
preferred creation path because it allocates IDs and supplies baseline
properties.

The future browser should use parameterized queries through an official Neo4j
driver and preserve the same business keys and controlled relationship types.

## Interchange and recovery

`phner graph export` creates a portable JSON snapshot for review and downstream
transformation. It is not a substitute for Neo4j database backups.

Operational recovery must use the backup or dump mechanism supported by the
deployed Neo4j edition. Credentials, database dumps, and exported production
data must not be committed to this repository.

The existing YAML loader and LinkML generation tools remain available for
interchange and migration work, but `data/` is no longer the canonical store.
