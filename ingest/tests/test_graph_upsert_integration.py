"""Neo4j integration tests for graph_upsert.

These run only when NEXUS_TEST_NEO4J_URI is set, pointing at a disposable
database (the docker-compose Neo4j is fine, but the tests wipe all nodes).

    export NEXUS_TEST_NEO4J_URI=bolt://localhost:7687
    export NEXUS_TEST_NEO4J_USERNAME=neo4j
    export NEXUS_TEST_NEO4J_PASSWORD=<password from .env>
    uv run pytest tests/test_graph_upsert_integration.py -v

Uniqueness constraints from api/src/main/resources/schema.cypher are not
required here: the writer merges on ids and this local system has a single
writer. Apply them with scripts/apply-schema.sh for the real database.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nexus_ingest.graph_upsert import WriteError, write_import
from nexus_ingest.models import FetchResult, ParseStats
from nexus_ingest.normalize import compute_record_hash
from nexus_ingest.source_config import load_source_config
from nexus_ingest.sources.ofac.parser import parse_sdn

NEO4J_URI = os.environ.get("NEXUS_TEST_NEO4J_URI")
pytestmark = pytest.mark.skipif(not NEO4J_URI, reason="NEXUS_TEST_NEO4J_URI is not set")

FIXTURE = Path(__file__).parent / "fixtures" / "ofac" / "sdn_happy.xml"
CONFIG = load_source_config("ofac")


def _driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            os.environ.get("NEXUS_TEST_NEO4J_USERNAME", "neo4j"),
            os.environ.get("NEXUS_TEST_NEO4J_PASSWORD", ""),
        ),
    )


def _fixture_records() -> list:
    stats = ParseStats()
    records = list(parse_sdn(FIXTURE, stats, dataset_id="ofac-sdn"))
    for record in records:
        record.record_hash = compute_record_hash(record)
    return records


def _fetch() -> FetchResult:
    return FetchResult(
        dataset_id="ofac-sdn",
        byte_count=2048,
        sha256="a" * 64,
        final_url="https://example.invalid/sdn.xml",
        requested_url="https://example.invalid/sdn.xml",
        status_code=200,
    )


def _run_id(serial: int) -> str:
    return f"ofac-sdn:20260916T12000{serial}Z:{'a' * 12}"


def _import_once(driver, records, serial: int):
    return write_import(
        driver,
        CONFIG,
        records,
        run_id=_run_id(serial),
        started_at=f"2026-09-16T12:00:0{serial}Z",
        fetch=_fetch(),
    )


def _wipe(session) -> None:
    session.run("MATCH (n) DETACH DELETE n")


def test_first_write_creates_the_expected_graph_shape() -> None:
    with _driver() as driver:
        with driver.session() as session:
            _wipe(session)
        stats = _import_once(driver, _fixture_records(), serial=0)

        assert (stats.inserted, stats.changed, stats.unchanged) == (5, 0, 0)
        assert stats.deactivated == 0

        with driver.session() as session:
            # 5 SourceRecord + 5 described Entity + 2 Entity:Address
            # + 1 Dataset + 1 ImportRun
            nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            rels = session.run(
                "MATCH ()-[r]->() RETURN count(r) AS c"
            ).single()["c"]
            # 5 FROM_DATASET + 5 OBSERVED_IN + 5 DESCRIBES + 2 LOCATED_AT
            assert (nodes, rels) == (14, 17)

            vessel = session.run(
                "MATCH (v:Vessel) RETURN v.imo AS imo, v.normalized_name AS name"
            ).single()
            assert vessel["imo"] == "9990001"
            assert vessel["name"] == "aurora"

            run = session.run(
                "MATCH (r:ImportRun {id: $id}) RETURN r.status AS status, "
                "r.record_count AS record_count",
                id=_run_id(0),
            ).single()
            assert run["status"] == "SUCCEEDED"
            assert run["record_count"] == 5

            inactive = session.run(
                "MATCH (sr:SourceRecord {dataset_id: 'ofac-sdn'}) "
                "WHERE sr.active = false RETURN count(sr) AS c"
            ).single()["c"]
            assert inactive == 0


def test_identical_second_write_reports_zero_changes() -> None:
    with _driver() as driver:
        with driver.session() as session:
            _wipe(session)
        _import_once(driver, _fixture_records(), serial=0)
        second = _import_once(driver, _fixture_records(), serial=1)

        assert second.inserted == 0
        assert second.changed == 0
        assert second.unchanged == 5
        assert second.deactivated == 0

        with driver.session() as session:
            still_active = session.run(
                "MATCH (sr:SourceRecord {dataset_id: 'ofac-sdn'}) "
                "WHERE sr.active = true RETURN count(sr) AS c"
            ).single()["c"]
            succeeded_runs = session.run(
                "MATCH (r:ImportRun) WHERE r.status = 'SUCCEEDED' "
                "RETURN count(r) AS c"
            ).single()["c"]
            total_records = session.run(
                "MATCH (sr:SourceRecord) RETURN count(sr) AS c"
            ).single()["c"]

            assert still_active == 5
            assert succeeded_runs == 2
            assert total_records == 5


def test_one_changed_field_changes_exactly_that_record() -> None:
    with _driver() as driver:
        with driver.session() as session:
            _wipe(session)
        _import_once(driver, _fixture_records(), serial=0)

        changed_records = _fixture_records()
        avery = next(r for r in changed_records if r.external_id == "10001")
        avery.aliases = ["A. Der Berg", "Completely Different Alias"]
        avery.record_hash = compute_record_hash(avery)

        second = _import_once(driver, changed_records, serial=1)

        assert (second.inserted, second.changed, second.unchanged) == (0, 1, 4)

        with driver.session() as session:
            stored = session.run(
                "MATCH (sr:SourceRecord {dataset_id: 'ofac-sdn', "
                "external_id: '10001'}) "
                "RETURN sr.id AS id, sr.record_hash AS hash, sr.active AS active"
            ).single()
            assert stored["id"] == "ofac-sdn:10001"
            assert stored["hash"] == avery.record_hash
            assert stored["active"] is True


def test_failed_run_deactivates_nothing() -> None:
    with _driver() as driver:
        with driver.session() as session:
            _wipe(session)
        _import_once(driver, _fixture_records(), serial=0)

        poisoned = _fixture_records()
        # An object the Neo4j driver cannot serialize forces a mid-import
        # failure after the run node exists.
        poisoned[0].programs = [object()]

        with pytest.raises(WriteError):
            _import_once(driver, poisoned, serial=1)

        with driver.session() as session:
            active = session.run(
                "MATCH (sr:SourceRecord {dataset_id: 'ofac-sdn'}) "
                "WHERE sr.active = true RETURN count(sr) AS c"
            ).single()["c"]
            failed_runs = session.run(
                "MATCH (r:ImportRun) WHERE r.status = 'FAILED' RETURN count(r) AS c"
            ).single()["c"]

            assert active == 5
            assert failed_runs == 1
