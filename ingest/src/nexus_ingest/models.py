"""Shared data shapes for the ingestion pipeline (PLAN.md T3.1).

Field sets here are draft scaffolding — finalize as each ingestor is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# OFAC SDN <SDNType> values: 1=Individual, 2=Entity, 3=Vessel, 4=Aircraft.
# Aircraft is out of scope for v1.


@dataclass
class SdnRecord:
    """One normalized record parsed from a source list."""

    source_id: str  # e.g. "ofac"
    external_id: str  # the list's own id
    record_type: str  # "person" | "organization" | "vessel"
    name: str
    aliases: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class UpsertStats:
    """Counters returned by every upsert — drives the idempotency checks."""

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class CypherParams:
    """A record mapped to Cypher MERGE parameters."""

    source_id: str
    source: dict[str, Any]
    entity_id: str  # deterministic composite, e.g. f"ofac:{sdn_id}" (T3.5)
    label: str  # "Person" | "Organization" | "Vessel"
    props: dict[str, Any]
