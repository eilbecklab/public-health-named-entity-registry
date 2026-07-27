# Public Health Named Entity Registry

PHNER is an empty-by-default, manually curated registry of public-health named
entities. LinkML is the authoritative structural schema; one-record-per-file
YAML is the authoritative data; generated files are disposable projections.

This repository contains the first executable draft of the curation system. It
does **not** contain production entities.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

phner validate registry
phner new source
phner new entity
phner find-duplicates
phner review registry
```

Complete the evidence record before referencing it from an entity. A newly
scaffolded template is intentionally incomplete and will fail validation until
a curator supplies the required facts.

Build a disposable development bundle with:

```bash
phner build
```

Prepare and verify a candidate release only after all canonical records pass
release policy:

```bash
phner release prepare --version 0.1.0
phner release verify build/
```

See [CURATION_GUIDE.md](CURATION_GUIDE.md) and
[RELEASE_GUIDE.md](RELEASE_GUIDE.md) for the full workflows. The plan assessment
and remaining governance decisions are in
[docs/strategy-review.md](docs/strategy-review.md).

Production curation must wait until the role assignments and initial policies
in [GOVERNANCE.md](GOVERNANCE.md) are approved. Governed decisions use the
[decision-record workflow](docs/decisions/README.md).

## Source-of-truth boundary

1. `src/public_health_named_entity_registry/schema/*.yaml` defines structure.
2. `data/` contains manually curated facts.
3. Governance documents define review and release policy.
4. `build/` and Neo4j are generated views, never master copies.

Candidate imports, synthetic fixtures, external geographic identifiers, and
automatic fact discovery are outside the canonical MVP path.
