"""Batch-upsert SDN records into Neo4j (PLAN.md T3.6)."""

from __future__ import annotations

from nexus_ingest.models import CypherParams, UpsertStats


def upsert_records(records: list[CypherParams], neo4j_session) -> UpsertStats:
    """Single UNWIND batch upsert (one query, not one per record).

    Labels can't be parameterized in Cypher — pick one-per-label or generic Entity
    + follow-up label set, and document the choice in a comment here.
    """
    raise NotImplementedError("T3.6")
