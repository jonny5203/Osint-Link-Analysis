// Nexus schema — the contract every service writes against.
// This file may safely be executed repeatedly.

// ---------------------------------------------------------
// Remove obsolete scaffold schema
// ---------------------------------------------------------

DROP INDEX person_name_lookup IF EXISTS;
DROP INDEX organization_name_lookup IF EXISTS;
DROP INDEX vessel_imo_lookup IF EXISTS;

DROP CONSTRAINT person_id IF EXISTS;
DROP CONSTRAINT organization_id IF EXISTS;
DROP CONSTRAINT vessel_id IF EXISTS;
DROP CONSTRAINT address_id IF EXISTS;
DROP CONSTRAINT source_id IF EXISTS;

// ---------------------------------------------------------
// Current uniqueness constraints
// ---------------------------------------------------------

// All searchable entities use the common Entity label
CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (entity:Entity)
REQUIRE entity.id IS UNIQUE;

// A Dataset identifies a stable source list.
CREATE CONSTRAINT dataset_id IF NOT EXISTS
FOR (dataset:Dataset)
REQUIRE dataset.id IS UNIQUE;

// An ImportRun identifies one import attempt.
CREATE CONSTRAINT import_run_id IF NOT EXISTS
FOR (run:ImportRun)
REQUIRE run.id IS UNIQUE;

// A SourceRecord identifies one publisher-controlled record.
CREATE CONSTRAINT source_record_id IF NOT EXISTS
FOR (record:SourceRecord)
REQUIRE record.id IS UNIQUE;

// An investigation contains analyst-created work.
CREATE CONSTRAINT investigation_iid IF NOT EXISTS
FOR (investigation:Investigation)
REQUIRE investigation.id IS UNIQUE;

// ---------------------------------------------------------
// Search and lookup indexes
// ---------------------------------------------------------

CREATE FULLTEXT INDEX entity_name_search IF NOT EXISTS
FOR (entity:Entity)
ON EACH [entity.display_name, entity.aliases];

CREATE INDEX source_record_external_id IF NOT EXISTS
FOR (record:SourceRecord)
ON (record.dataset_id, record.external_id);

CREATE INDEX vessel_imo IF NOT EXISTS
FOR (vessel:Vessel)
ON (vessel.imo);
