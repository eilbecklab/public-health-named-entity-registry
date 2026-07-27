// PHNER Neo4j graph contract.
// Migrations are applied by `phner graph init` and recorded as PhnerMigration nodes.

CREATE CONSTRAINT phner_entity_id_unique IF NOT EXISTS
FOR (entity:NamedEntity) REQUIRE entity.entity_id IS UNIQUE;

CREATE CONSTRAINT phner_evidence_source_id_unique IF NOT EXISTS
FOR (source:EvidenceSource) REQUIRE source.source_id IS UNIQUE;

CREATE CONSTRAINT phner_participation_id_unique IF NOT EXISTS
FOR (participation:PlatformParticipation) REQUIRE participation.participation_id IS UNIQUE;

CREATE CONSTRAINT phner_counter_kind_unique IF NOT EXISTS
FOR (counter:PhnerCounter) REQUIRE counter.kind IS UNIQUE;

CREATE CONSTRAINT phner_migration_name_unique IF NOT EXISTS
FOR (migration:PhnerMigration) REQUIRE migration.name IS UNIQUE;

CREATE INDEX phner_entity_preferred_name IF NOT EXISTS
FOR (entity:NamedEntity) ON (entity.preferred_name);

CREATE INDEX phner_entity_type IF NOT EXISTS
FOR (entity:NamedEntity) ON (entity.entity_type);
