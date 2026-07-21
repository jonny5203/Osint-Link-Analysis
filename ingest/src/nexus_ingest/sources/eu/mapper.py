"""Map an EU record to Cypher params (PLAN.md T4.2). Entity id format: eu:<eu_id>."""

from __future__ import annotations

from nexus_ingest.models import CypherParams, SdnRecord


def map_record(rec: SdnRecord) -> CypherParams:
    raise NotImplementedError("T4.2")
