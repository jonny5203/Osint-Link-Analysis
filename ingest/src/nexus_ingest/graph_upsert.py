"""Neo4j writer for one finished parse pass.

This module owns every write the ingestion pipeline performs. The Spring API
stays read-only by design, so this is the only code that creates Dataset,
ImportRun, SourceRecord, and source Entity nodes.

Safety rules the whole module is built around:

-   Nodes come from MERGE on their id values, never CREATE. Running the same
    import twice must converge on the same graph.
-   A node's labels are always Entity plus one concrete label from
    LABEL_BY_KIND. A label never comes from source text.
-   Change accounting is read from what Cypher returns, comparing the stored
    record_hash against the incoming one. Nothing here guesses counts.
-   Deactivation happens only in the same transaction that marks the run
    SUCCEEDED, after every batch succeeded. A failed run deactivates nothing
    and deletes nothing.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

from nexus_ingest.models import (
    AddressField,
    EntityKind,
    FetchResult,
    NormalizedRecord,
    WriteStats,
)
from nexus_ingest.normalize import normalize_address, normalize_text
from nexus_ingest.source_config import SourceConfig

LABEL_BY_KIND: dict[EntityKind, str] = {
    EntityKind.PERSON: "Person",
    EntityKind.ORGANIZATION: "Organization",
    EntityKind.VESSEL: "Vessel",
}

_KIND_BY_LABEL: dict[str, EntityKind] = {
    label: kind for kind, label in LABEL_BY_KIND.items()
}

BATCH_SIZE = 500


class WriteError(RuntimeError):
    """Raised when records are not safe to write or a batch fails."""


def connect_to_graph():
    """Open a driver from NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD.

    Values may come from a local .env file, which python-dotenv loads here.
    """
    from dotenv import load_dotenv

    load_dotenv()
    uri = os.environ.get("NEO4J_URI")
    if not uri:
        raise WriteError("NEO4J_URI is not set, so there is no graph to write to")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    return GraphDatabase.driver(uri, auth=(user, password))


def source_record_id(dataset_id: str, external_id: str) -> str:
    """Compose the stable id of a SourceRecord.

    The dataset prefix is what keeps external id 10001 from OFAC and a future
    10001 from another publisher from ever colliding.
    """
    return f"{dataset_id}:{external_id}"


def entity_node_id(record_id: str) -> str:
    """Every source record describes exactly one entity of its own."""
    return f"entity:{record_id}"


def address_node_id(record_id: str, index: int) -> str:
    """The i-th address of one record, in the order the publisher listed them."""
    return f"address:{record_id}:{index}"


def write_import(
    driver,
    config: SourceConfig,
    records: list[NormalizedRecord],
    *,
    run_id: str,
    started_at: str,
    fetch: FetchResult,
) -> WriteStats:
    """Write one import run and return what happened, counted from Cypher results.

    The order matters for safety. The Dataset node and the ImportRun node are
    created first, with the run marked FETCHED. Records are then upserted
    batch by batch. Only when every batch succeeded does one final transaction
    mark the run SUCCEEDED and deactivate this dataset's records that the run
    did not observe. If any batch raises, the run is marked FAILED and
    nothing is deactivated.
    """
    _require_writable(records)
    rows_by_label = build_upsert_rows(records)

    stats = WriteStats()
    finished_at = _utc_now_iso()

    with driver.session() as session:
        session.execute_write(
            _create_dataset_and_run,
            config=config,
            run_id=run_id,
            started_at=started_at,
            fetch=fetch,
        )
        try:
            for label, rows in rows_by_label.items():
                for start in range(0, len(rows), BATCH_SIZE):
                    batch = rows[start : start + BATCH_SIZE]
                    outcome = upsert_record_batch(session, label, batch, config.dataset_id, run_id)
                    stats.inserted += outcome["inserted"]
                    stats.changed += outcome["changed"]
                    stats.unchanged += outcome["unchanged"]
        except Exception as err:
            _mark_run_failed(session, run_id, err)
            raise WriteError(f"import {run_id} failed during record upsert: {err}") from err

        stats.deactivated = session.execute_write(
            finalize_successful_import,
            run_id=run_id,
            dataset_id=config.dataset_id,
            record_count=len(records),
            stats=stats,
            finished_at=finished_at,
        )

    return stats


def build_upsert_rows(records: list[NormalizedRecord]) -> dict[str, list[dict]]:
    """Turn hashed records into parameter rows grouped by graph label.

    Each row carries the ids and stored properties one upsert statement
    needs. Originals keep the publisher's spelling. The comparison values
    come from normalize_text() and normalize_address(). Address rows get
    their indexed ids here so the statement can merge them without
    recomputing anything. Keys follow EntityKind declaration order, so the
    grouping never depends on the order records were met in.
    """
    grouped: dict[str, list[dict]] = {}

    for record in records:
        source_id = source_record_id(record.dataset_id, record.external_id)
        row = {
            "sr_id": source_id,
            "entity_id": entity_node_id(source_id),
            "external_id": record.external_id,
            "record_hash": record.record_hash,
            "display_name": record.display_name,
            "normalized_name": normalize_text(record.display_name),
            "aliases": record.aliases,
            "dates_of_birth": [date.raw for date in record.dates_of_birth],
            "nationalities": record.nationalities,
            "programs": record.programs,
            "imo": record.vessel.imo if record.vessel else None,
            "flag": record.vessel.flag if record.vessel else None,
            "addresses": [
                {
                    "id": address_node_id(source_id, index),
                    "display_name": _address_display_name(address),
                    "normalized_address": normalize_address(address),
                }
                for index, address in enumerate(record.addresses)
            ],
        }
        grouped.setdefault(LABEL_BY_KIND[record.kind], []).append(row)

    return {
        label: grouped[label] for label in LABEL_BY_KIND.values() if label in grouped
    }


def _address_display_name(address: AddressField) -> str:
    """One printable line from the fields the publisher filled in."""
    parts = [
        part
        for part in (
            address.line1,
            address.line2,
            address.city,
            address.region,
            address.postal_code,
            address.country,
        )
        if part
    ]
    return ", ".join(parts)


def upsert_record_batch(
    session,
    label: str,
    rows: list[dict],
    dataset_id: str,
    run_id: str,
) -> dict[str, int]:
    """Upsert one batch of same-kind records and classify each outcome.

    One UNWIND statement merges the SourceRecord, Entity, and Entity:Address
    nodes with their provenance edges. The stored record_hash is captured
    into stored_hash before the SET overwrites it, and that snapshot decides
    inserted, changed, or unchanged. Values travel as parameters. Only the
    label is interpolated, and write_import has already checked it against
    LABEL_BY_KIND. The kind property needs the uppercase enum value, which
    _KIND_BY_LABEL looks up from the same allowlist.

    Addresses run inside FOREACH rather than UNWIND on purpose. An UNWIND
    over an empty address list would drop the whole row from the query, and
    records without addresses must still be merged and classified.
    """
    kind = _KIND_BY_LABEL[label].value
    now = _utc_now_iso()

    outcome_rows = session.run(
        f"""
        UNWIND $rows AS row
        MERGE (sr:SourceRecord {{id: row.sr_id}})
        ON CREATE SET sr.first_seen_at = $now
        WITH sr, row, sr.record_hash AS stored_hash
        SET sr.dataset_id = $dataset_id,
            sr.external_id = row.external_id,
            sr.record_hash = row.record_hash,
            sr.last_seen_at = $now,
            sr.active = true,
            sr.programs = row.programs
        MERGE (e:Entity:{label} {{id: row.entity_id}})
        SET e.kind = $kind,
            e.display_name = row.display_name,
            e.normalized_name = row.normalized_name,
            e.aliases = row.aliases,
            e.dates_of_birth = row.dates_of_birth,
            e.nationalities = row.nationalities,
            e.imo = row.imo,
            e.flag = row.flag
        MERGE (d:Dataset {{id: $dataset_id}})
        MERGE (r:ImportRun {{id: $run_id}})
        MERGE (sr)-[:FROM_DATASET]->(d)
        MERGE (sr)-[:OBSERVED_IN]->(r)
        MERGE (sr)-[:DESCRIBES]->(e)
        FOREACH (address IN row.addresses |
            MERGE (a:Entity:Address {{id: address.id}})
            SET a.kind = 'ADDRESS',
                a.display_name = address.display_name,
                a.normalized_address = address.normalized_address
            MERGE (e)-[located:LOCATED_AT]->(a)
            SET located.evidence_record_ids = [row.sr_id]
        )
        WITH sr, row, stored_hash,
             CASE
                 WHEN stored_hash IS NULL THEN 'inserted'
                 WHEN stored_hash <> row.record_hash THEN 'changed'
                 ELSE 'unchanged'
             END AS outcome
        RETURN outcome, count(*) AS n
        """,
        rows=rows,
        now=now,
        kind=kind,
        dataset_id=dataset_id,
        run_id=run_id,
    ).data()

    counts = {"inserted": 0, "changed": 0, "unchanged": 0}
    for counted in outcome_rows:
        counts[counted["outcome"]] = counted["n"]
    return counts


def finalize_successful_import(
    tx,
    *,
    run_id: str,
    dataset_id: str,
    record_count: int,
    stats: WriteStats,
    finished_at: str,
) -> int:
    """Mark the run SUCCEEDED and sweep unobserved records, in one transaction.

    Both statements run inside the single transaction handed in as tx. The
    counts make the run satisfy record_count = inserted + updated + unchanged
    + failed, with stats.changed stored as updated_count. The sweep then flips
    active to false on this dataset's records that have no OBSERVED_IN edge
    to this run, and the number of flipped records comes back from the query.
    Records are never deleted.
    """

    tx.run(
        """
            MATCH (r:ImportRun {id: $run_id})
            SET r.status = 'SUCCEEDED',
                r.finished_at = $finished_at,
                r.record_count = $record_count,
                r.inserted_count = $inserted,
                r.updated_count = $updated,
                r.unchanged_count = $unchanged,
                r.failed_count = $failed
        """,
        run_id=run_id,
        finished_at=finished_at,
        record_count=record_count,
        inserted=stats.inserted,
        updated=stats.changed,
        unchanged=stats.unchanged,
        failed=stats.failed,
    )

    deactivated = tx.run(
        """
            MATCH (sr:SourceRecord)
            WHERE sr.dataset_id = $dataset_id
              AND sr.active = true
              AND NOT (sr)-[:OBSERVED_IN]->(:ImportRun {id: $run_id})
            SET sr.active = false
            RETURN count(sr) AS deactivated
        """,
        dataset_id=dataset_id,
        run_id=run_id,
    )

    return deactivated.single()["deactivated"]


def _require_writable(records: list[NormalizedRecord]) -> None:
    """Refuse records that never finished the pipeline, naming each offender.

    An unhashed record would make change accounting meaningless, and a kind
    outside LABEL_BY_KIND has no safe label to wear. Both checks run before
    any database connection is used.
    """
    for record in records:
        if record.record_hash is None:
            raise WriteError(
                f"record {record.dataset_id}:{record.external_id} has no record_hash"
            )
        if record.kind not in LABEL_BY_KIND:
            raise WriteError(
                f"record {record.dataset_id}:{record.external_id} has kind "
                f"{record.kind}, which has no allowlisted graph label"
            )


def _create_dataset_and_run(
    tx,
    *,
    config: SourceConfig,
    run_id: str,
    started_at: str,
    fetch: FetchResult,
) -> None:
    """Create this run's anchor nodes before any record is touched.

    The Dataset is merged because it is the same stable publisher product on
    every run. The ImportRun is created because every run is its own event,
    even when nothing changed.
    """
    tx.run(
        """
        MERGE (d:Dataset {id: $dataset_id})
        SET d.name = $name,
            d.publisher = $publisher,
            d.landing_url = $landing_url
        CREATE (r:ImportRun {
            id: $run_id,
            dataset_id: $dataset_id,
            started_at: $started_at,
            status: 'FETCHED',
            download_url: $download_url,
            sha256: $sha256
        })
        """,
        dataset_id=config.dataset_id,
        name=config.dataset_id,
        publisher=config.publisher,
        landing_url=config.landing_url,
        run_id=run_id,
        started_at=started_at,
        download_url=fetch.final_url or fetch.requested_url,
        sha256=fetch.sha256,
    )


def _mark_run_failed(session, run_id: str, err: Exception) -> None:
    """Leave a visible FAILED status with the error text, best effort.

    No record state is touched here. That is the point: a failed run must
    leave every active flag exactly as it was.
    """
    try:
        session.run(
            """
            MATCH (r:ImportRun {id: $run_id})
            SET r.status = 'FAILED',
                r.error = $error
            """,
            run_id=run_id,
            error=str(err)[:500],
        )
    except Exception:
        pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
