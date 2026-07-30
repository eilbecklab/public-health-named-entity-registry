# Excel intake workbook

The [working DHHS intake workbook](../intake/PHNER-US-FED-DHHS.xlsx) is a structured
staging area for gathering information before loading reviewed records into
Neo4j. It is intended to make early research and collaborative data entry
easier; it does not replace Neo4j as the canonical graph.

The working workbook is versioned and published with this public repository.
Do not enter private, confidential, restricted, or otherwise unsuitable
information. Use the
[blank workbook template](../templates/phner-intake-template.xlsx) whenever a
fresh copy is needed.

## Recommended workflow

1. Add one real-world entity per row in **Entities**.
2. Use `parent_intake_key` for the internal organizational hierarchy.
3. Add alternate or historical names in **Names** when needed.
4. Use **Relationships** for connections not represented by the parent
   hierarchy.
5. Review the workbook before preparing a Neo4j import.

Use temporary keys such as `ENT-001` and `REL-001`. These keys connect rows
across sheets during intake. Do not manually assign `phner-*` identifiers; the
Neo4j loading workflow must allocate permanent IDs safely.

Green headers marked with an asterisk are required. Blue headers are optional.
Dropdowns enforce single-valued controlled fields. Where a cell permits several
values, enter repository-controlled values separated by semicolons.

The workbook currently supports structured collection and review. It is not
automatically synchronized with Neo4j, and the repository does not yet provide
a spreadsheet import command. Keep the original workbook as an intake artifact
and import only a reviewed copy.

## Review the hierarchy

The `parent_intake_key` column in **Entities** defines the internal hierarchy.
The final `breadcrumb` column is a calculated display path used to distinguish
repeated names; edit the name or parent key rather than the breadcrumb formula.

## Regenerate the template

The blank template copies the current working workbook's sheets, columns,
formatting, formulas, validation, guides, and lookup values. It then clears
entered records from **Entities**, **Relationships**, and **Names**:

```bash
python scripts/generate_intake_workbook.py
```

Regenerate it whenever the working workbook's structure or controls change,
then review the template before committing it. This command deliberately does
not overwrite `intake/PHNER-US-FED-DHHS.xlsx`.
