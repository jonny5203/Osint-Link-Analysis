"""Parse the OFAC SDN XML into shared NormalizedRecords.

The live list uses textual sdnType values (Individual, Entity, Vessel,
Aircraft); Aircraft entries are counted as unsupported, never silently
dropped. Parsing itself is not implemented yet.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from nexus_ingest.models import NormalizedRecord


def parse_sdn(xml_path: Path) -> Iterator[NormalizedRecord]:
    """Stream the XML with lxml.etree.iterparse; never load the whole file."""
    raise NotImplementedError("parse_sdn: OFAC SDN XML parsing not implemented yet")
