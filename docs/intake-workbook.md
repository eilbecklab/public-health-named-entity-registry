# Excel intake workbook

The [PHNER graph intake workbook](../templates/phner-intake-template.xlsx) is a
structured staging area for gathering information before loading reviewed
records into Neo4j. It is intended to make early research and collaborative
data entry easier; it does not replace Neo4j as the canonical graph.

Make a copy before entering data:

```bash
mkdir -p work
cp templates/phner-intake-template.xlsx work/phner-intake.xlsx
```

The repository ignores `work/` to avoid publishing incomplete or sensitive
research accidentally. Store and back up the working copy according to the
data it contains.

## Recommended workflow

1. Record supporting webpages, reports, directories, and documents in
   **Sources**.
2. Add one real-world entity per row in **Entities**.
3. Add alternate or historical names in **Names** and physical locations in
   **Locations** as needed.
4. Add a relationship only after both endpoint entities exist.
5. Use **Platform Participations** when an entity's interaction with a platform
   needs roles, lifecycle status, environments, or data-exchange details.
6. Review the workbook before preparing a Neo4j import.

Use temporary keys such as `ENT-001`, `REL-001`, `SRC-001`, and `PAR-001`.
These keys connect rows across sheets during intake. Do not manually assign
`phner-*` identifiers; the Neo4j loading workflow must allocate permanent IDs
safely.

Green headers marked with an asterisk are required. Blue headers are optional.
Dropdowns enforce single-valued controlled fields. Where a cell permits several
values, enter repository-controlled values separated by semicolons.

The workbook currently supports structured collection and review. It is not
automatically synchronized with Neo4j, and the repository does not yet provide
a spreadsheet import command. Keep the original workbook as an intake artifact
and import only a reviewed copy.

## Regenerate the template

The committed workbook is generated from the controlled values and Neo4j
relationship rules in `mappings/`:

```bash
python scripts/generate_intake_workbook.py
```

Regenerate it whenever controlled vocabulary changes, then review the workbook
before committing the updated binary file.
