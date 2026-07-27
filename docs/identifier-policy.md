# Identifier policy

Canonical identifiers are opaque, global, and stable:

```text
phner-ent-000001
phner-rel-000001
phner-par-000001
phner-src-000001
phner-release-2026-001
```

Names, slugs, country codes, URLs, and external identifiers never determine a
PHNER ID. Retired IDs are not reused. True splits, mergers, or replacements
receive new entity IDs and explicit historical relationships.

The CLI updates a tracked monotonic ledger atomically and also scans existing
canonical files. Git cannot coordinate unmerged branches, so branch collisions
remain a curator-visible merge task.

