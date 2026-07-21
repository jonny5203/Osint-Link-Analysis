"""Shared ingestor shape (PLAN.md T4.1).

Every source (OFAC / EU / UN) implements this so the pipeline is uniform:
fetch -> parse -> map -> upsert -> verify idempotency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from nexus_ingest.models import CypherParams, SdnRecord, UpsertStats


class Ingestor(ABC):
    """Abstract ingestor. Subclasses set `source_id` and implement the 4 steps."""

    source_id: str  # "ofac" | "eu" | "un"

    @abstractmethod
    def fetch(self, force: bool = False) -> Path: ...

    @abstractmethod
    def parse(self, raw_path: Path) -> list[SdnRecord]: ...

    @abstractmethod
    def map(self, record: SdnRecord) -> CypherParams: ...

    @abstractmethod
    def upsert(self, records: list[CypherParams]) -> UpsertStats: ...
