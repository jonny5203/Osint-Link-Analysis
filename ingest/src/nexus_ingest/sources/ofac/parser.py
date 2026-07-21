"""Parse the OFAC SDN XML into normalized records (PLAN.md T3.3)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from nexus_ingest.models import SdnRecord


def parse_sdn(xml_path: Path) -> Iterator[SdnRecord]:
    """Stream-parse the XML with lxml.etree.iterparse (do not load the whole file).

    Map <SDNType> 1->Person, 2->Organization, 3->Vessel (4=Aircraft, out of scope).
    """
    raise NotImplementedError("T3.3")
