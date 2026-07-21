"""Batch-upsert EU records (PLAN.md T4.2). Reuses the OFAC UNWIND pattern."""

from __future__ import annotations

from nexus_ingest.models import CypherParams, UpsertStats


def upsert_records(records: list[CypherParams], neo4j_session) -> UpsertStats:
    raise NotImplementedError("T4.2")
