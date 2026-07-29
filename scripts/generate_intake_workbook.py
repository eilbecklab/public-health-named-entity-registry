#!/usr/bin/env python3
"""Generate the PHNER Excel intake workbook from repository-controlled values."""

from __future__ import annotations

import argparse
import datetime as dt
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "templates" / "phner-intake-template.xlsx"
CONTROLLED_VALUES_PATH = PROJECT_ROOT / "mappings" / "controlled_values.yaml"
RELATIONSHIP_RULES_PATH = PROJECT_ROOT / "mappings" / "relationship_rules.yaml"

MAX_DATA_ROW = 1001
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
REQUIRED_HEADER_FILL = PatternFill("solid", fgColor="0F6B4F")
SECTION_FILL = PatternFill("solid", fgColor="D9EAF7")
INPUT_FILL = PatternFill("solid", fgColor="FFFDF2")
INVALID_FILL = PatternFill("solid", fgColor="F4CCCC")
KEY_FILL = PatternFill("solid", fgColor="E2F0D9")
WHITE_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(size=18, bold=True, color="1F4E78")
SUBTITLE_FONT = Font(size=12, bold=True, color="0F6B4F")
THIN_GRAY_BORDER = Border(
    bottom=Side(style="thin", color="D9E1F2"),
)

RELATIONSHIP_MEANINGS = {
    "PART_OF": "Administrative or organizational component of",
    "SERVES_JURISDICTION": "Has an official or recognized service scope for",
    "WITHIN_JURISDICTION": "Jurisdiction is contained by another jurisdiction",
    "LOCATED_IN": "Has physical presence in a jurisdiction",
    "HEADQUARTERED_IN": "Has principal headquarters in a jurisdiction",
    "REGISTERED_IN": "Is legally or formally registered in a jurisdiction",
    "OPERATES_IN": "Conducts operations in a jurisdiction",
    "HAS_GEOGRAPHIC_SCOPE": "Covers a region without implying authority",
    "PARTICIPATES_IN": "Participates in a program, network, group, or platform",
    "MEMBER_OF": "Is a recognized member of a network or group",
    "OPERATED_BY": "Facility, program, group, or platform is operated by",
    "SPONSORED_BY": "Program, initiative, network, or group is sponsored by",
    "FUNDED_BY": "Receives funding from",
    "COLLABORATES_WITH": "Symmetric collaboration",
    "SUCCESSOR_OF": "Replaced an earlier, non-identical entity",
    "PREDECESSOR_OF": "Was replaced by a later, non-identical entity",
    "SAME_AS": "Exact identity after explicit human review",
}


class Column:
    """A column in an intake sheet."""

    def __init__(
        self,
        name: str,
        description: str,
        *,
        required: bool = False,
        width: int = 18,
        validation: str | None = None,
        kind: str = "text",
    ) -> None:
        self.name = name
        self.description = description
        self.required = required
        self.width = width
        self.validation = validation
        self.kind = kind


SHEET_COLUMNS: dict[str, list[Column]] = {
    "Entities": [
        Column(
            "intake_key",
            "Your temporary unique key, such as ENT-001. Do not enter a PHNER ID.",
            required=True,
            width=16,
            kind="key",
        ),
        Column("preferred_name", "Current display name.", required=True, width=34),
        Column(
            "entity_type",
            "Select one entity type.",
            required=True,
            width=23,
            validation="EntityTypes",
        ),
        Column(
            "status",
            "Current lifecycle status.",
            required=True,
            width=15,
            validation="EntityStatuses",
        ),
        Column(
            "assertion_status",
            "Use provisional while gathering or reviewing information.",
            required=True,
            width=18,
            validation="AssertionStatuses",
        ),
        Column(
            "steward",
            "Person or group responsible for this record.",
            required=True,
            width=24,
        ),
        Column(
            "classifications",
            "Zero or more controlled classifications separated by semicolons.",
            width=36,
            kind="multi",
        ),
        Column(
            "jurisdiction_scopes",
            "Zero or more controlled jurisdiction scopes separated by semicolons.",
            width=28,
            kind="multi",
        ),
        Column("valid_from", "Start date, if known.", width=14, kind="date"),
        Column("valid_to", "End date, if known.", width=14, kind="date"),
        Column(
            "official_urls",
            "One or more full URLs separated by semicolons.",
            width=38,
            kind="multi",
        ),
        Column(
            "source_keys",
            "Supporting Sources.intake_key values separated by semicolons.",
            width=28,
            kind="multi",
        ),
        Column("reviewed_by", "Most recent reviewer, if reviewed.", width=22),
        Column("last_reviewed", "Most recent review date.", width=16, kind="date"),
        Column("notes", "Curation notes; do not put secrets here.", width=42),
    ],
    "Relationships": [
        Column(
            "intake_key",
            "Your temporary unique key, such as REL-001.",
            required=True,
            width=16,
            kind="key",
        ),
        Column(
            "subject_intake_key",
            "Entities.intake_key at the start of the directed relationship.",
            required=True,
            width=22,
            validation="EntityKeys",
        ),
        Column(
            "relationship_type",
            "Select a controlled relationship type.",
            required=True,
            width=24,
            validation="RelationshipTypes",
        ),
        Column(
            "object_intake_key",
            "Entities.intake_key at the end of the directed relationship.",
            required=True,
            width=22,
            validation="EntityKeys",
        ),
        Column("valid_from", "Start date, if known.", width=14, kind="date"),
        Column("valid_to", "End date, if known.", width=14, kind="date"),
        Column(
            "source_keys",
            "Supporting Sources.intake_key values separated by semicolons.",
            required=True,
            width=28,
            kind="multi",
        ),
        Column(
            "assertion_status",
            "Use provisional while gathering or reviewing information.",
            required=True,
            width=18,
            validation="AssertionStatuses",
        ),
        Column("steward", "Person or group responsible for this assertion.", required=True),
        Column(
            "identity_reviewed_by",
            "Required only for SAME_AS.",
            width=24,
        ),
        Column(
            "identity_reviewed_at",
            "Required only for SAME_AS.",
            width=20,
            kind="date",
        ),
        Column(
            "identity_rationale",
            "Required only for SAME_AS; explain why the two records are identical.",
            width=42,
        ),
        Column("notes", "Curation notes; do not put secrets here.", width=42),
    ],
    "Sources": [
        Column(
            "intake_key",
            "Your temporary unique key, such as SRC-001.",
            required=True,
            width=16,
            kind="key",
        ),
        Column(
            "source_type",
            "Select the kind of source.",
            required=True,
            width=25,
            validation="SourceTypes",
        ),
        Column("title", "Human-readable source title.", required=True, width=42),
        Column("publisher", "Organization or person publishing the source.", width=30),
        Column("url", "Full URL, when applicable.", width=45),
        Column("document_identifier", "DOI, report number, or other identifier.", width=28),
        Column("retrieved_at", "Date the source was accessed.", width=16, kind="date"),
        Column(
            "locator",
            "Page, section, table, heading, or other precise locator.",
            width=30,
        ),
        Column("content_hash", "Optional SHA-256 hash for a captured document.", width=28),
        Column("notes", "Source or evidence notes; do not paste sensitive content.", width=42),
    ],
    "Names": [
        Column(
            "entity_intake_key",
            "The related Entities.intake_key.",
            required=True,
            width=22,
            validation="EntityKeys",
        ),
        Column(
            "value", "Alias, former name, abbreviation, or other name.", required=True, width=38
        ),
        Column(
            "name_type",
            "Select the kind of name.",
            required=True,
            width=20,
            validation="NameTypes",
        ),
        Column("language", "BCP 47 language tag when known, such as en or fr-CA.", width=16),
        Column(
            "is_official",
            "Whether an authoritative source presents this as an official name.",
            width=15,
            validation="BooleanValues",
        ),
        Column("valid_from", "Start date, if known.", width=14, kind="date"),
        Column("valid_to", "End date, if known.", width=14, kind="date"),
        Column(
            "source_keys",
            "Supporting Sources.intake_key values separated by semicolons.",
            width=28,
            kind="multi",
        ),
    ],
    "Locations": [
        Column(
            "entity_intake_key",
            "The related Entities.intake_key.",
            required=True,
            width=22,
            validation="EntityKeys",
        ),
        Column(
            "location_type",
            "Select the kind of location.",
            width=20,
            validation="LocationTypes",
        ),
        Column(
            "address_lines",
            "Street/address lines separated by semicolons.",
            width=38,
            kind="multi",
        ),
        Column("locality", "City, town, or locality.", width=24),
        Column("administrative_area_text", "State, province, territory, etc.", width=27),
        Column("postal_code", "Postal or ZIP code.", width=16),
        Column(
            "jurisdiction_intake_key",
            "Entities.intake_key for the jurisdiction, when represented.",
            width=25,
            validation="EntityKeys",
        ),
        Column("latitude", "Decimal latitude.", width=15, kind="decimal"),
        Column("longitude", "Decimal longitude.", width=15, kind="decimal"),
        Column("valid_from", "Start date, if known.", width=14, kind="date"),
        Column("valid_to", "End date, if known.", width=14, kind="date"),
        Column(
            "source_keys",
            "Supporting Sources.intake_key values separated by semicolons.",
            width=28,
            kind="multi",
        ),
    ],
    "Platform Participations": [
        Column(
            "intake_key",
            "Your temporary unique key, such as PAR-001.",
            required=True,
            width=16,
            kind="key",
        ),
        Column(
            "entity_intake_key",
            "The participating Entities.intake_key.",
            required=True,
            width=22,
            validation="EntityKeys",
        ),
        Column(
            "platform_intake_key",
            "The Entities.intake_key whose type is platform.",
            required=True,
            width=22,
            validation="EntityKeys",
        ),
        Column(
            "roles",
            "One or more controlled participation roles separated by semicolons.",
            required=True,
            width=32,
            kind="multi",
        ),
        Column(
            "lifecycle_status",
            "Current status of the participation.",
            required=True,
            width=20,
            validation="ParticipationStatuses",
        ),
        Column(
            "environments",
            "Controlled deployment environments separated by semicolons.",
            width=28,
            kind="multi",
        ),
        Column(
            "data_exchange_modes",
            "Controlled exchange modes separated by semicolons.",
            width=32,
            kind="multi",
        ),
        Column(
            "capabilities",
            "Free-text capabilities separated by semicolons.",
            width=34,
            kind="multi",
        ),
        Column("valid_from", "Start date, if known.", width=14, kind="date"),
        Column("valid_to", "End date, if known.", width=14, kind="date"),
        Column(
            "source_keys",
            "Supporting Sources.intake_key values separated by semicolons.",
            required=True,
            width=28,
            kind="multi",
        ),
        Column(
            "assertion_status",
            "Use provisional while gathering or reviewing information.",
            required=True,
            width=18,
            validation="AssertionStatuses",
        ),
        Column("steward", "Person or group responsible for this assertion.", required=True),
        Column("notes", "Curation notes; do not put secrets here.", width=42),
    ],
}

LOOKUP_KEYS = {
    "EntityTypes": "entity_types",
    "EntityStatuses": "entity_statuses",
    "AssertionStatuses": "assertion_statuses",
    "EntityClassifications": "entity_classifications",
    "JurisdictionScopes": "jurisdiction_scopes",
    "NameTypes": "name_types",
    "LocationTypes": "location_types",
    "SourceTypes": "source_types",
    "ParticipationRoles": "participation_roles",
    "ParticipationStatuses": "participation_statuses",
    "DeploymentEnvironments": "deployment_environments",
    "DataExchangeModes": "data_exchange_modes",
}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping."""
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def controlled_list(values: dict[str, Any], key: str) -> list[str]:
    """Return one list of repository-controlled values."""
    raw = values.get(key)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"Expected a non-empty list for {key}")
    if not all(isinstance(value, str) and value for value in raw):
        raise ValueError(f"Controlled values for {key} must be non-empty strings")
    return raw


def add_title(
    sheet: Worksheet,
    title: str,
    subtitle: str | None = None,
    *,
    end_column: int = 8,
) -> int:
    """Add a title block and return the next available row."""
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_column)
    title_cell = sheet.cell(1, 1, title)
    title_cell.font = TITLE_FONT
    title_cell.alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 28
    if subtitle:
        sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_column)
        subtitle_cell = sheet.cell(2, 1, subtitle)
        subtitle_cell.font = Font(italic=True, color="666666")
        subtitle_cell.alignment = Alignment(wrap_text=True, vertical="top")
        sheet.row_dimensions[2].height = 32
        return 4
    return 3


def add_instruction_sheet(workbook: Workbook) -> None:
    """Build the Instructions sheet."""
    sheet = workbook.active
    sheet.title = "Instructions"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 95
    row = add_title(
        sheet,
        "PHNER graph intake workbook",
        (
            "Use this workbook to gather and review information before assigning permanent "
            "PHNER identifiers and loading records into Neo4j."
        ),
        end_column=6,
    )

    sections: list[tuple[str, Sequence[str]]] = [
        (
            "Recommended order",
            [
                "1. Add each supporting webpage, report, directory, or document to Sources.",
                "2. Add one row per real-world entity to Entities.",
                "3. Add aliases and former names to Names; add physical sites to Locations.",
                "4. Add directed connections only after both endpoint entities exist.",
                "5. Use Platform Participations when an entity has roles or lifecycle details "
                "on a platform.",
                "6. Review required fields and highlighted warnings before preparing an import.",
            ],
        ),
        (
            "Keys and permanent IDs",
            [
                "Create short, unique temporary keys such as ENT-001, REL-001, SRC-001, "
                "and PAR-001.",
                "Use those keys for references between sheets.",
                "Do not invent phner-ent-, phner-rel-, phner-src-, or phner-par- identifiers. "
                "Permanent IDs are assigned during loading into Neo4j.",
            ],
        ),
        (
            "Data-entry rules",
            [
                "Enter data in a working copy, not in the blank template committed to Git.",
                "A green header with an asterisk is required; a blue header is optional.",
                "Use dropdown values exactly as supplied. The Lookup Values sheet contains all "
                "controlled vocabularies.",
                "For a cell that permits several values, separate values with semicolons, for "
                "example: public_health_organization; federal_agency.",
                "Use real Excel dates displayed as YYYY-MM-DD. Leave unknown dates blank.",
                "Relationships are directional: subject → relationship type → object.",
                "Use assertion_status=provisional while information is still being gathered.",
                "Do not add, remove, rename, or reorder columns if the workbook will be imported.",
                "Do not store passwords, private personal data, or confidential source "
                "material here.",
            ],
        ),
        (
            "Minimum useful first pass",
            [
                "Complete Sources and Entities first. Names, Locations, Relationships, and "
                "Platform Participations can be added later.",
                "For Entities, focus on intake_key, preferred_name, entity_type, status, "
                "assertion_status, steward, official_urls, and source_keys.",
                "The workbook is an intake artifact, not the canonical graph. Neo4j remains the "
                "authoritative operational store after import.",
            ],
        ),
    ]

    for heading, lines in sections:
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        cell = sheet.cell(row, 1, heading)
        cell.font = SUBTITLE_FONT
        cell.fill = SECTION_FILL
        cell.alignment = Alignment(vertical="center")
        row += 1
        for line in lines:
            sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            cell = sheet.cell(row, 1, line)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = THIN_GRAY_BORDER
            sheet.row_dimensions[row].height = 31
            row += 1
        row += 1

    sheet.column_dimensions["A"].width = 31
    for column in range(2, 7):
        sheet.column_dimensions[get_column_letter(column)].width = 18
    sheet.freeze_panes = "A4"


def add_named_range(workbook: Workbook, name: str, formula: str) -> None:
    """Create a workbook-scoped named range."""
    workbook.defined_names.add(DefinedName(name, attr_text=formula))


def add_lookup_sheet(
    workbook: Workbook,
    controlled_values: dict[str, Any],
    relationship_rules: dict[str, Any],
) -> None:
    """Build the controlled-vocabulary sheet and named ranges."""
    sheet = workbook.create_sheet("Lookup Values")
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    sheet.sheet_view.zoomScale = 85

    lookup_values: dict[str, list[str]] = {
        display_name: controlled_list(controlled_values, key)
        for display_name, key in LOOKUP_KEYS.items()
    }
    lookup_values["RelationshipTypes"] = list(relationship_rules)
    lookup_values["BooleanValues"] = ["TRUE", "FALSE"]

    for column_index, (name, values) in enumerate(lookup_values.items(), start=1):
        header = sheet.cell(1, column_index, name)
        header.fill = HEADER_FILL
        header.font = WHITE_FONT
        header.alignment = Alignment(wrap_text=True)
        sheet.column_dimensions[get_column_letter(column_index)].width = max(
            18,
            min(34, max(len(name), *(len(value) for value in values)) + 2),
        )
        for row_index, value in enumerate(values, start=2):
            sheet.cell(row_index, column_index, value)
        range_formula = (
            f"{quote_sheetname(sheet.title)}!"
            f"${get_column_letter(column_index)}$2:"
            f"${get_column_letter(column_index)}${len(values) + 1}"
        )
        add_named_range(workbook, name, range_formula)
    max_lookup_length = max(len(values) for values in lookup_values.values()) + 1
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(lookup_values))}{max_lookup_length}"


def add_data_validation(
    sheet: Worksheet,
    column_letter: str,
    named_range: str,
    *,
    allow_blank: bool,
) -> None:
    """Apply a named-list dropdown to a data column."""
    validation = DataValidation(
        type="list",
        formula1=f"={named_range}",
        allow_blank=allow_blank,
    )
    validation.error = "Select a value from the dropdown list."
    validation.errorTitle = "Value outside the graph contract"
    validation.prompt = "Select a repository-controlled value."
    validation.promptTitle = "Controlled value"
    validation.showErrorMessage = True
    validation.showInputMessage = True
    sheet.add_data_validation(validation)
    validation.add(f"{column_letter}2:{column_letter}{MAX_DATA_ROW}")


def add_required_formatting(sheet: Worksheet, columns: Sequence[Column]) -> None:
    """Highlight duplicate keys and required blanks on populated rows."""
    duplicate_formula = f'AND($A2<>"",COUNTIF($A$2:$A${MAX_DATA_ROW},$A2)>1)'
    sheet.conditional_formatting.add(
        f"A2:A{MAX_DATA_ROW}",
        FormulaRule(formula=[duplicate_formula], fill=INVALID_FILL),
    )

    for column_index, column in enumerate(columns, start=1):
        if not column.required:
            continue
        letter = get_column_letter(column_index)
        formula = f'AND($A2<>"",{letter}2="")'
        sheet.conditional_formatting.add(
            f"{letter}2:{letter}{MAX_DATA_ROW}",
            FormulaRule(formula=[formula], fill=INVALID_FILL),
        )


def add_data_sheet(workbook: Workbook, title: str, columns: Sequence[Column]) -> None:
    """Build a formatted intake data sheet."""
    sheet = workbook.create_sheet(title)
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 85
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{MAX_DATA_ROW}"

    for column_index, column in enumerate(columns, start=1):
        header_text = f"{column.name} *" if column.required else column.name
        cell = sheet.cell(1, column_index, header_text)
        cell.fill = REQUIRED_HEADER_FILL if column.required else HEADER_FILL
        cell.font = WHITE_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.comment = Comment(column.description, "PHNER")
        sheet.column_dimensions[get_column_letter(column_index)].width = column.width

        if column.kind == "date":
            for row_index in range(2, MAX_DATA_ROW + 1):
                sheet.cell(row_index, column_index).number_format = "yyyy-mm-dd"
        elif column.kind == "decimal":
            for row_index in range(2, MAX_DATA_ROW + 1):
                sheet.cell(row_index, column_index).number_format = "0.000000"
        elif column.kind == "key":
            for row_index in range(2, MAX_DATA_ROW + 1):
                sheet.cell(row_index, column_index).fill = KEY_FILL

        if column.validation:
            add_data_validation(
                sheet,
                get_column_letter(column_index),
                column.validation,
                allow_blank=not column.required,
            )

    sheet.row_dimensions[1].height = 42
    for row_index in range(2, 102):
        for column_index in range(1, len(columns) + 1):
            sheet.cell(row_index, column_index).alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    # Include the first empty entry row in the table so Excel expands it naturally.
    table = Table(
        displayName=title.replace(" ", ""),
        ref=f"A1:{get_column_letter(len(columns))}2",
    )
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(table)
    add_required_formatting(sheet, columns)


def format_type_list(value: Any) -> str:
    """Format a relationship-rule endpoint list for display."""
    if not value:
        return "any entity type"
    if not isinstance(value, list):
        raise ValueError("Expected a relationship endpoint list")
    return "; ".join(str(item) for item in value)


def add_relationship_guide(
    workbook: Workbook,
    relationship_rules: dict[str, Any],
) -> None:
    """Build a human-readable relationship reference sheet."""
    sheet = workbook.create_sheet("Relationship Guide")
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    sheet.sheet_view.zoomScale = 90
    headers = [
        "relationship_type",
        "meaning",
        "allowed_subject_types",
        "allowed_object_types",
        "direction/rule notes",
    ]
    widths = [24, 43, 50, 43, 48]
    for column_index, (header, width) in enumerate(zip(headers, widths, strict=True), start=1):
        cell = sheet.cell(1, column_index, header)
        cell.fill = HEADER_FILL
        cell.font = WHITE_FONT
        cell.alignment = Alignment(wrap_text=True)
        sheet.column_dimensions[get_column_letter(column_index)].width = width

    for row_index, (relationship_type, rules) in enumerate(
        relationship_rules.items(),
        start=2,
    ):
        if not isinstance(rules, dict):
            raise ValueError(f"Expected relationship rules for {relationship_type}")
        notes = []
        if rules.get("symmetric"):
            notes.append("Symmetric")
        if rules.get("acyclic"):
            notes.append("Must remain acyclic")
        if rules.get("max_current_objects"):
            notes.append(f"At most {rules['max_current_objects']} current object(s)")
        if rules.get("inverse"):
            notes.append(f"Inverse: {rules['inverse']}")
        if rules.get("requires_identity_review"):
            notes.append("Requires explicit identity review")
        values = [
            relationship_type,
            RELATIONSHIP_MEANINGS.get(relationship_type, ""),
            format_type_list(rules.get("subject_types")),
            format_type_list(rules.get("object_types")),
            "; ".join(notes),
        ]
        for column_index, value in enumerate(values, start=1):
            cell = sheet.cell(row_index, column_index, value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = THIN_GRAY_BORDER
        sheet.row_dimensions[row_index].height = 34

    last_row = len(relationship_rules) + 1
    table = Table(displayName="RelationshipReference", ref=f"A1:E{last_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(table)


def add_example_sheet(workbook: Workbook) -> None:
    """Build a small, clearly non-importable example sheet."""
    sheet = workbook.create_sheet("Examples")
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 90
    row = add_title(
        sheet,
        "Synthetic examples",
        "These rows demonstrate how sheets reference one another. Do not copy them as real data.",
        end_column=8,
    )

    examples: list[tuple[str, list[str], list[list[str]]]] = [
        (
            "Sources",
            ["intake_key", "source_type", "title", "publisher", "url", "retrieved_at"],
            [
                [
                    "SRC-001",
                    "official_web_page",
                    "Example agency — About us",
                    "Example agency",
                    "https://example.org/about",
                    "2026-07-29",
                ]
            ],
        ),
        (
            "Entities",
            [
                "intake_key",
                "preferred_name",
                "entity_type",
                "status",
                "assertion_status",
                "steward",
                "source_keys",
            ],
            [
                [
                    "ENT-001",
                    "Example Health Agency",
                    "organization",
                    "active",
                    "provisional",
                    "Example curator",
                    "SRC-001",
                ],
                [
                    "ENT-002",
                    "Example Jurisdiction",
                    "jurisdiction",
                    "active",
                    "provisional",
                    "Example curator",
                    "SRC-001",
                ],
            ],
        ),
        (
            "Relationships",
            [
                "intake_key",
                "subject_intake_key",
                "relationship_type",
                "object_intake_key",
                "source_keys",
                "assertion_status",
                "steward",
            ],
            [
                [
                    "REL-001",
                    "ENT-001",
                    "SERVES_JURISDICTION",
                    "ENT-002",
                    "SRC-001",
                    "provisional",
                    "Example curator",
                ]
            ],
        ),
    ]

    for heading, headers, rows in examples:
        sheet.cell(row, 1, heading).font = SUBTITLE_FONT
        sheet.cell(row, 1).fill = SECTION_FILL
        row += 1
        for column_index, header in enumerate(headers, start=1):
            cell = sheet.cell(row, column_index, header)
            cell.fill = HEADER_FILL
            cell.font = WHITE_FONT
        row += 1
        for values in rows:
            for column_index, value in enumerate(values, start=1):
                cell = sheet.cell(row, column_index, value)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.fill = INPUT_FILL
            row += 1
        row += 2

    widths = [18, 31, 24, 24, 22, 22, 26, 24]
    for column_index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(column_index)].width = width


def create_workbook() -> Workbook:
    """Create the complete intake workbook."""
    controlled_values = load_yaml(CONTROLLED_VALUES_PATH)
    relationship_rules = load_yaml(RELATIONSHIP_RULES_PATH)

    workbook = Workbook()
    workbook.properties.creator = "PHNER contributors"
    workbook.properties.title = "PHNER graph intake workbook"
    workbook.properties.subject = "Structured intake for the Public Health Named Entity Registry"
    workbook.properties.description = (
        "A non-canonical workbook for gathering entities, relationships, and evidence "
        "before loading them into Neo4j."
    )
    workbook.properties.keywords = "PHNER, Neo4j, public health, named entities"
    fixed_timestamp = dt.datetime(2026, 7, 29, 0, 0, 0)
    workbook.properties.created = fixed_timestamp
    workbook.properties.modified = fixed_timestamp
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True

    add_instruction_sheet(workbook)
    add_lookup_sheet(workbook, controlled_values, relationship_rules)

    # EntityKeys can be used by other sheets even before the Entities sheet is created.
    add_named_range(
        workbook,
        "EntityKeys",
        f"{quote_sheetname('Entities')}!$A$2:$A${MAX_DATA_ROW}",
    )
    add_named_range(
        workbook,
        "SourceKeys",
        f"{quote_sheetname('Sources')}!$A$2:$A${MAX_DATA_ROW}",
    )

    for sheet_name in [
        "Entities",
        "Names",
        "Locations",
        "Relationships",
        "Platform Participations",
        "Sources",
    ]:
        add_data_sheet(workbook, sheet_name, SHEET_COLUMNS[sheet_name])

    add_relationship_guide(workbook, relationship_rules)
    add_example_sheet(workbook)

    # Put the sheets in workflow order while keeping reference material at the end.
    desired_order = [
        "Instructions",
        "Entities",
        "Relationships",
        "Sources",
        "Names",
        "Locations",
        "Platform Participations",
        "Relationship Guide",
        "Lookup Values",
        "Examples",
    ]
    workbook._sheets = [workbook[name] for name in desired_order]
    workbook.active = 0
    return workbook


def validate_workbook(workbook: Workbook) -> None:
    """Fail fast when generator output is structurally incomplete."""
    expected_sheets = {
        "Instructions",
        "Entities",
        "Relationships",
        "Sources",
        "Names",
        "Locations",
        "Platform Participations",
        "Relationship Guide",
        "Lookup Values",
        "Examples",
    }
    if set(workbook.sheetnames) != expected_sheets:
        raise ValueError("Workbook sheet set does not match the intake contract")

    for sheet_name, columns in SHEET_COLUMNS.items():
        sheet = workbook[sheet_name]
        actual_headers = [sheet.cell(1, index).value for index in range(1, len(columns) + 1)]
        expected_headers = [
            f"{column.name} *" if column.required else column.name for column in columns
        ]
        if actual_headers != expected_headers:
            raise ValueError(f"Header mismatch in {sheet_name}")
        if not sheet.data_validations.dataValidation:
            raise ValueError(f"No dropdown validations found in {sheet_name}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Workbook destination (default: {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)})",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    """Generate and save the workbook."""
    args = parse_args(argv)
    output = args.output.resolve()
    workbook = create_workbook()
    validate_workbook(workbook)
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
