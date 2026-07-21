"""Map a UN record to Cypher params (PLAN.md T4.4). Entity id format: un:<un_id>."""

from __future__ import annotations

from nexus_ingest.models import CypherParams, SdnRecord


def map_record(rec: SdnRecord) -> CypherParams:
    raise NotImplementedError("T4.4")
