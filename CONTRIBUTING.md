# Contributing

Keep graph-contract changes small and reviewable. Git changes cover Cypher
migrations, entity-label mappings, relationship rules, validation, interchange
schemas, tests, and documentation. Canonical entity edits happen in Neo4j.

Do not commit production exports, database dumps, credentials, scraped records,
real entities in test fixtures, or generated `build/` files. Schema and
vocabulary changes require tests and a numbered migration when existing graph
data is affected.

Before opening a pull request, run:

```bash
pytest
ruff check .
mypy
```

When a disposable Neo4j test database is available, also run:

```bash
phner graph init
phner graph validate
```

Routine curation may proceed under approved policy. Create a
[governance decision record](docs/decisions/README.md) when a change involves:

- `SAME_AS`, a merge, split, retirement, or rename-versus-replacement decision;
- a new or changed relationship or controlled-vocabulary value;
- registry scope, schema, validation, or release-policy changes;
- disputed-assertion resolution;
- external identifier schemes;
- breaking downstream or Neo4j projection changes.

The decision record, tests, migration, and affected documentation should
normally be reviewed in the same pull request.

Exploratory graph construction may use `assertion_status: provisional`.
Production publication requirements can be tightened after the graph model and
editing workflow have been proven.

The pull request template contains the curation and governance checklist.
