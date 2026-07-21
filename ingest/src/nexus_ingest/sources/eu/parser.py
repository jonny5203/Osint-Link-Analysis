"""Parse the EU consolidated list (PLAN.md T4.2)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from nexus_ingest.models import SdnRecord


def parse_eu(xml_path: Path) -> Iterator[SdnRecord]:
    # EU schema differs from OFAC: publication references, separate name parts.
    raise NotImplementedError("T4.2")
