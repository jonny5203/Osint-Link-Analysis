"""Shared-neutral data shapes for the ingestion pipeline.

Every sanctions publisher (OFAC for now and UN later) parses its raw files into the same
NormalizedRecord shape, so normalization, hashing, and the Neo4j writer never know which
publisher produced a record.

Convention carried by these models:
-   Oiriginal publisher spellings are always preserved.
    Comparison-friendly forms are derived later in normalize.py, never stored here as replacement.
-   Timestamps are UTC ISO-8601 strings, e.g. "2026-08-24T10:00:00Z"
    because that is what the graph fixture and the Java API reads.
-   Entity kind values are the exact strings the Java EntityKind enum parses (PERSON, ORGANIZATION, VESSEL, ADDRESS)
    GraphQueryService.java calls EntityKind.valueof("kind)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class EntityKind(str, Enum):
    """Browsable node kinds.

    Inheriting from str means the Neo4j driver serializes these values as
    their plain string ("PERSON") without the writer calling .value first.
    """

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    VESSEL = "VESSEL"
    ADDRESS = "ADDRESS"


@dataclass
class PartialDate:
    """Dates that the publisher only knows part of.

    OFAC birth dates arrive as free text such as "18 Mar 1980" or just "1976".
    Turning those into datetime.date would invent precision the source never claimed,
    so the raw string is preserved and the year is stored only when the publisher actually states one.
    """

    raw: str
    year: int | None = None


@dataclass
class AddressField:
    """One postal address exactly as the publisher recorded it."""

    line1: str = ""
    line2: str = ""
    city: str = ""
    region: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class IdentifierField:
    """One publisher issued identifier (passport, registration, IMO, ...)"""

    id_type: str
    number: str
    country: str | None = None


@dataclass
class VesselInfo:
    """Vessel only attributes, stays None on every other kind of record"""

    vessel_type: str | None = None
    flag: str | None = None
    imo: str | None = None


@dataclass
class NormalizedRecord:
    """One publisher record in the shared source-neutral shape.

    record_hash starts empty and is filled by normalized.compute_record_hash() before the
    record reaches the write. The writer refuses unhashed records because it has to make sure
    all the stages has been reached, and compares stoed vs incoming hashes.
    """

    dataset_id: str
    external_id: str
    kind: EntityKind
    display_name: str
    aliases: list[str] = field(default_factory=list)
    addresses: list[AddressField] = field(default_factory=list)
    identifiers: list[IdentifierField] = field(default_factory=list)
    programs: list[str] = field(default_factory=list)
    dates_of_birth: list[PartialDate] = field(default_factory=list)
    places_of_birth: list[str] = field(default_factory=list)
    nationalities: list[str] = field(default_factory=list)
    title: str | None = None
    remarks: str | None = None
    vessel: VesselInfo | None = None
    record_hash: str | None = None


@dataclass
class FetchResult:
    """Outcome of getting the raw bytes for one import.

    The network fields stay None when the run used  -- file to read a local snapshot
    instead of downloading, this is for one shape covers both entry points.
    """

    dataset_id: str
    byte_count: int
    sha256: str
    snapshot_path: Path | None = None
    requested_url: str | None = None
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    from_cache: bool = False
    from_file: bool = False


@dataclass
class ParseFailure:
    """One record the parser could not turn into a NormalizedRecord."""

    external_id: str | None
    reason: str


@dataclass
class ParseStats:
    """Counts what happened to every record the parser read.

    Each record ends up in one of three groups. It was parsed into a NormalizedRecord.
    It was skipped becuase we do not support its type, or it failed. The three groups counts
    must add up to the total records read. If they do not add up then a record was lost and nobody noticed
    """

    encountered: int = 0
    supported: int = 0
    unsupported_by_reason: dict[str, int] = field(default_factory=dict)
    failures: list[ParseFailure] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return len(self.failures)

    @property
    def unsupported_total(self) -> int:
        """Total records skipped by policy (aircraft) or unknown type."""
        return sum(self.unsupported_by_reason.values())

    def reconciles(self) -> bool:
        """True when every encountered record was accountede for somewhere."""
        return (
            self.supported + self.unsupported_total + len(self.failures)
            == self.encountered
        )


@dataclass
class WriteStats:
    """Neo4j write outcomes, counted from returned Cypher results.

    changed is written to the graphs as updated_count, the property name fixtures/demo/fixture.cypher and invariant 4 already use.
    Deactivated counts records from earlier snapshots that the post success sweep marked active=false, records are never deleted.
    """

    inserted: int = 0
    changed: int = 0
    unchanged: int = 0
    failed: int = 0
    deactivated: int = 0


@dataclass
class ImportReport:
    """Everything one import attempt did, serialized under data/reports.

    write is None for dry runs, which by desing never open a Neo4j connection. run_id follows
    "<dataset-id>:<UTC timesamp>:<first 12 sha256 chars>".
    """

    run_id: str
    dataset_id: str
    mode: str
    status: str
    started_at: str
    finished_at: str
    fetch: FetchResult
    parse: ParseStats
    write: WriteStats | None = None
    parser_format_version: int = 1
    error: str | None = None
