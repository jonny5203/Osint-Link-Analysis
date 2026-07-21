// Nexus deterministic demo fixture.
//
// All people, organizations, addresses, identifiers, datasets, and
// relationships in this file are fictional. They exist only for automated
// testing and local demonstrations. Do not use them for factual claims.
//
// The fixture is idempotent: stable IDs and MERGE allow it to be loaded more
// than once without creating duplicate nodes or relationships.

// ---------------------------------------------------------------------------
// Datasets and successful import runs
// ---------------------------------------------------------------------------

MERGE (alpha:Dataset {id: "fixture:dataset:alpha"})
SET alpha.name = "Fictional Dataset Alpha",
    alpha.publisher = "Nexus Test Fixtures",
    alpha.landing_url = "local://fixtures/demo/alpha";

MERGE (beta:Dataset {id: "fixture:dataset:beta"})
SET beta.name = "Fictional Dataset Beta",
    beta.publisher = "Nexus Test Fixtures",
    beta.landing_url = "local://fixtures/demo/beta";

MERGE (alphaRun:ImportRun {
    id: "fixture:import:alpha:20260720T100000Z:aaaaaaaaaaaa"
})
SET alphaRun.dataset_id = "fixture:dataset:alpha",
    alphaRun.started_at = "2026-07-20T10:00:00Z",
    alphaRun.finished_at = "2026-07-20T10:00:01Z",
    alphaRun.status = "SUCCEEDED",
    alphaRun.download_url = "local://fixtures/demo/alpha",
    alphaRun.sha256 =
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    alphaRun.record_count = 4,
    alphaRun.inserted_count = 4,
    alphaRun.updated_count = 0,
    alphaRun.unchanged_count = 0,
    alphaRun.failed_count = 0;

MERGE (betaRun:ImportRun {
    id: "fixture:import:beta:20260720T100000Z:bbbbbbbbbbbb"
})
SET betaRun.dataset_id = "fixture:dataset:beta",
    betaRun.started_at = "2026-07-20T10:00:00Z",
    betaRun.finished_at = "2026-07-20T10:00:01Z",
    betaRun.status = "SUCCEEDED",
    betaRun.download_url = "local://fixtures/demo/beta",
    betaRun.sha256 =
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    betaRun.record_count = 1,
    betaRun.inserted_count = 1,
    betaRun.updated_count = 0,
    betaRun.unchanged_count = 0,
    betaRun.failed_count = 0;

// ---------------------------------------------------------------------------
// Source records
// ---------------------------------------------------------------------------

MERGE (record:SourceRecord {id: "fixture:record:alpha:avery"})
SET record.dataset_id = "fixture:dataset:alpha",
    record.external_id = "avery-001",
    record.record_hash =
        "1111111111111111111111111111111111111111111111111111111111111111",
    record.first_seen_at = "2026-07-20T10:00:00Z",
    record.last_seen_at = "2026-07-20T10:00:00Z",
    record.active = true;

MERGE (record:SourceRecord {id: "fixture:record:alpha:northstar"})
SET record.dataset_id = "fixture:dataset:alpha",
    record.external_id = "northstar-001",
    record.record_hash =
        "2222222222222222222222222222222222222222222222222222222222222222",
    record.first_seen_at = "2026-07-20T10:00:00Z",
    record.last_seen_at = "2026-07-20T10:00:00Z",
    record.active = true;

MERGE (record:SourceRecord {id: "fixture:record:alpha:blue-harbor"})
SET record.dataset_id = "fixture:dataset:alpha",
    record.external_id = "blue-harbor-001",
    record.record_hash =
        "3333333333333333333333333333333333333333333333333333333333333333",
    record.first_seen_at = "2026-07-20T10:00:00Z",
    record.last_seen_at = "2026-07-20T10:00:00Z",
    record.active = true;

MERGE (record:SourceRecord {id: "fixture:record:alpha:aurora-tide"})
SET record.dataset_id = "fixture:dataset:alpha",
    record.external_id = "aurora-tide-001",
    record.record_hash =
        "4444444444444444444444444444444444444444444444444444444444444444",
    record.first_seen_at = "2026-07-20T10:00:00Z",
    record.last_seen_at = "2026-07-20T10:00:00Z",
    record.active = true;

MERGE (record:SourceRecord {id: "fixture:record:beta:avery"})
SET record.dataset_id = "fixture:dataset:beta",
    record.external_id = "avery-beta-009",
    record.record_hash =
        "5555555555555555555555555555555555555555555555555555555555555555",
    record.first_seen_at = "2026-07-20T10:00:00Z",
    record.last_seen_at = "2026-07-20T10:00:00Z",
    record.active = true;

// ---------------------------------------------------------------------------
// Browsable entities
// ---------------------------------------------------------------------------

MERGE (avery:Entity:Person {id: "fixture:entity:avery"})
SET avery.kind = "PERSON",
    avery.display_name = "Avery Stone",
    avery.normalized_name = "avery stone",
    avery.aliases = ["A. Stone"];

MERGE (averyVariant:Entity:Person {id: "fixture:entity:avery-variant"})
SET averyVariant.kind = "PERSON",
    averyVariant.display_name = "Avery J. Stone",
    averyVariant.normalized_name = "avery j stone",
    averyVariant.aliases = ["Avery Stone"];

MERGE (northstar:Entity:Organization {id: "fixture:entity:northstar"})
SET northstar.kind = "ORGANIZATION",
    northstar.display_name = "Northstar Trading Ltd",
    northstar.normalized_name = "northstar trading ltd",
    northstar.aliases = [];

MERGE (blueHarbor:Entity:Organization {id: "fixture:entity:blue-harbor"})
SET blueHarbor.kind = "ORGANIZATION",
    blueHarbor.display_name = "Blue Harbor Holdings",
    blueHarbor.normalized_name = "blue harbor holdings",
    blueHarbor.aliases = [];

MERGE (aurora:Entity:Vessel {id: "fixture:entity:aurora-tide"})
SET aurora.kind = "VESSEL",
    aurora.display_name = "Aurora Tide",
    aurora.normalized_name = "aurora tide",
    aurora.aliases = [],
    aurora.imo = "9990001",
    aurora.flag = "NO";

MERGE (averyAddress:Entity:Address {id: "fixture:address:avery:0"})
SET averyAddress.kind = "ADDRESS",
    averyAddress.display_name = "10 Example Street, Oslo",
    averyAddress.normalized_address = "10 example street oslo",
    averyAddress.aliases = [];

MERGE (northstarAddress:Entity:Address {id: "fixture:address:northstar:0"})
SET northstarAddress.kind = "ADDRESS",
    northstarAddress.display_name = "20 Fictional Avenue, Bergen",
    northstarAddress.normalized_address = "20 fictional avenue bergen",
    northstarAddress.aliases = [];

MERGE (blueHarborAddress:Entity:Address {
    id: "fixture:address:blue-harbor:0"
})
SET blueHarborAddress.kind = "ADDRESS",
    blueHarborAddress.display_name = "30 Demonstration Road, Tromso",
    blueHarborAddress.normalized_address = "30 demonstration road tromso",
    blueHarborAddress.aliases = [];

// ---------------------------------------------------------------------------
// Provenance relationships
// ---------------------------------------------------------------------------

MATCH (dataset:Dataset {id: "fixture:dataset:alpha"})
MATCH (run:ImportRun {
    id: "fixture:import:alpha:20260720T100000Z:aaaaaaaaaaaa"
})
UNWIND [
    {
        recordId: "fixture:record:alpha:avery",
        entityId: "fixture:entity:avery"
    },
    {
        recordId: "fixture:record:alpha:northstar",
        entityId: "fixture:entity:northstar"
    },
    {
        recordId: "fixture:record:alpha:blue-harbor",
        entityId: "fixture:entity:blue-harbor"
    },
    {
        recordId: "fixture:record:alpha:aurora-tide",
        entityId: "fixture:entity:aurora-tide"
    }
] AS mapping
MATCH (record:SourceRecord {id: mapping.recordId})
MATCH (entity:Entity {id: mapping.entityId})
MERGE (record)-[:FROM_DATASET]->(dataset)
MERGE (record)-[:OBSERVED_IN]->(run)
MERGE (record)-[:DESCRIBES]->(entity);

MATCH (dataset:Dataset {id: "fixture:dataset:beta"})
MATCH (run:ImportRun {
    id: "fixture:import:beta:20260720T100000Z:bbbbbbbbbbbb"
})
MATCH (record:SourceRecord {id: "fixture:record:beta:avery"})
MATCH (entity:Entity {id: "fixture:entity:avery-variant"})
MERGE (record)-[:FROM_DATASET]->(dataset)
MERGE (record)-[:OBSERVED_IN]->(run)
MERGE (record)-[:DESCRIBES]->(entity);

// ---------------------------------------------------------------------------
// Analyst-facing graph relationships
// ---------------------------------------------------------------------------

MATCH (avery:Entity:Person {id: "fixture:entity:avery"})
MATCH (northstar:Entity:Organization {id: "fixture:entity:northstar"})
MERGE (avery)-[relationship:OWNS]->(northstar)
SET relationship.evidence_record_ids = [
    "fixture:record:alpha:avery",
    "fixture:record:alpha:northstar"
];

MATCH (northstar:Entity:Organization {id: "fixture:entity:northstar"})
MATCH (blueHarbor:Entity:Organization {id: "fixture:entity:blue-harbor"})
MERGE (northstar)-[relationship:CONTROLS]->(blueHarbor)
SET relationship.evidence_record_ids = [
    "fixture:record:alpha:northstar",
    "fixture:record:alpha:blue-harbor"
];

MATCH (blueHarbor:Entity:Organization {id: "fixture:entity:blue-harbor"})
MATCH (aurora:Entity:Vessel {id: "fixture:entity:aurora-tide"})
MERGE (blueHarbor)-[relationship:OWNS]->(aurora)
SET relationship.evidence_record_ids = [
    "fixture:record:alpha:blue-harbor",
    "fixture:record:alpha:aurora-tide"
];

MATCH (avery:Entity:Person {id: "fixture:entity:avery"})
MATCH (address:Entity:Address {id: "fixture:address:avery:0"})
MERGE (avery)-[relationship:LOCATED_AT]->(address)
SET relationship.evidence_record_ids = ["fixture:record:alpha:avery"];

MATCH (northstar:Entity:Organization {id: "fixture:entity:northstar"})
MATCH (address:Entity:Address {id: "fixture:address:northstar:0"})
MERGE (northstar)-[relationship:LOCATED_AT]->(address)
SET relationship.evidence_record_ids = ["fixture:record:alpha:northstar"];

MATCH (blueHarbor:Entity:Organization {id: "fixture:entity:blue-harbor"})
MATCH (address:Entity:Address {id: "fixture:address:blue-harbor:0"})
MERGE (blueHarbor)-[relationship:LOCATED_AT]->(address)
SET relationship.evidence_record_ids = [
    "fixture:record:alpha:blue-harbor"
];

// The two Avery entities intentionally remain separate. Phase 7 evaluates them
// and may add SAME_AS or POSSIBLE_MATCH without deleting either entity.
