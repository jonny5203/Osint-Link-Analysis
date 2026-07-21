"""Parse the UN consolidated list (PLAN.md T4.4)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from nexus_ingest.models import SdnRecord


def parse_un(xml_path: Path) -> Iterator[SdnRecord]:
    # UN schema: <ENTITIES>/<ENTITY>/<ENTITY_TYPE> ...
    raise NotImplementedError("T4.4")
