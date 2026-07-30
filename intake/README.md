# Versioned intake data

Edit [PHNER-US-FED-DHHS.xlsx](PHNER-US-FED-DHHS.xlsx) to gather graph records.
This working workbook is committed and pushed with the rest of the repository.

The **Entities** tab is the source of truth for the DHHS hierarchy. The
`breadcrumb` column is calculated by Excel from `preferred_name` and
`parent_intake_key`; do not type into that column.

The repository is public. Do not add private, confidential, restricted, or
otherwise unsuitable information.

The generator updates only the blank workbook under `templates/`; it does not
overwrite this working file.
