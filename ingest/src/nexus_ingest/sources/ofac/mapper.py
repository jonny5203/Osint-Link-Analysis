"""Map an SDN record to Cypher MERGE params (PLAN.md T3.5)."""

from __future__ import annotations

from nexus_ingest.models import CypherParams, SdnRecord


def map_record(rec: SdnRecord) -> CypherParams:
    """Convert SdnRecord -> CypherParams. Entity id is deterministic: f"ofac:{external_id}"."""
    raise NotImplementedError("T3.5")
