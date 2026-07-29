# Relationship guide

Relationships are directional, evidence-backed records. Their endpoints always
use PHNER entity IDs.

| Code | Curator meaning |
|---|---|
| `PART_OF` | Administrative or organizational component of |
| `SERVES_JURISDICTION` | Has an official or recognized service scope for |
| `WITHIN_JURISDICTION` | Jurisdiction is contained by another jurisdiction |
| `LOCATED_IN` | Has physical presence in a jurisdiction |
| `HEADQUARTERED_IN` | Has principal headquarters in a jurisdiction |
| `REGISTERED_IN` | Is legally or formally registered in a jurisdiction |
| `OPERATES_IN` | Conducts operations in a jurisdiction |
| `HAS_GEOGRAPHIC_SCOPE` | Covers a region without implying authority |
| `PARTICIPATES_IN` | Participates in a program, network, group, or platform |
| `MEMBER_OF` | Is a recognized member of a network or group |
| `OPERATED_BY` | Facility, program, group, or platform is operated by |
| `SPONSORED_BY` | Program, initiative, network, or group is sponsored by |
| `FUNDED_BY` | Receives funding from |
| `COLLABORATES_WITH` | Symmetric collaboration |
| `SUCCESSOR_OF` | Replaced an earlier, non-identical entity |
| `PREDECESSOR_OF` | Was replaced by a later, non-identical entity |
| `SAME_AS` | Exact identity after explicit identity review |

Do not substitute `PART_OF` for service jurisdiction or location. Do not use a
generic `RELATED_TO`. Platform interaction belongs in a participation record
when it carries roles, lifecycle, or environment details.

`SAME_AS` requires evidence and explicit identity-review metadata. It must never
be generated from name similarity or a shared external identifier.

Machine-enforced endpoint, acyclicity, and cardinality policies live in
`mappings/relationship_rules.yaml`.
