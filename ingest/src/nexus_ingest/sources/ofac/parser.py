"""Stream-parser for the legacy OFAC SDN.XML product.

The document root is sdnList and each entry is one sdnEntry child. The stable
key of a record is its uid. OFAC has changed the XML namespace before, so
nothing here may depend on a namespace URI: every element lookup goes through
the local-name helpers in xml_stream.py. Aircraft entries are real data that
v1 deliberately keeps out of the graph, so the parser counts each one as
unsupported instead of dropping it silently. Every sdnEntry met must end up in
exactly one bucket of the ParseStats, or a record was lost unseen.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from nexus_ingest.models import (
    AddressField,
    EntityKind,
    IdentifierField,
    NormalizedRecord,
    ParseFailure,
    ParseStats,
    PartialDate,
    VesselInfo,
)
from nexus_ingest.sources.xml_stream import (
    child_elements,
    child_text,
    stream_entries,
)

VESSEL_REGISTRATION_ID_TYPE = "Vessel Registration Identification"

_YEAR_IN_TEXT = re.compile(r"\b(\d{4})\b")


def parse_sdn(
    xml_path: Path, stats: ParseStats, dataset_id: str
) -> Iterator[NormalizedRecord]:
    """Stream one SDN.XML file into NormalizedRecord values.

    Yields only records this pipeline stores. Aircraft and unknown types are
    counted in stats.unsupported_by_reason, broken entries in stats.failures.
    The record_hash stays None here; hashing is a separate pipeline step that
    runs after parsing.
    """
    for entry in stream_entries(xml_path, "sdnEntry"):
        stats.encountered += 1

        uid = child_text(entry, "uid")

        # An entry without a uid has no identity. Count it as failed and move
        # on, so one broken entry never stops the rest of the file.
        if uid is None:
            stats.failures.append(ParseFailure(external_id=None, reason="missing_uid"))
            continue

        kind, unsupported_reason = map_sdn_type(child_text(entry, "sdnType"))
        if kind is None:
            stats.unsupported_by_reason[unsupported_reason] = (
                stats.unsupported_by_reason.get(unsupported_reason, 0) + 1
            )
            continue

        vessel = VesselInfo() if kind is EntityKind.VESSEL else None

        stats.supported += 1
        yield NormalizedRecord(
            dataset_id=dataset_id,
            external_id=uid,
            kind=kind,
            display_name=_display_name(entry, kind),
            aliases=_aliases(entry),
            addresses=extract_addresses(entry),
            identifiers=extract_identifiers(entry, vessel),
            programs=_texts_under(entry, "programList", "program"),
            dates_of_birth=_dates_of_birth(entry),
            places_of_birth=_texts_under(
                entry, "placeOfBirthList", "placeOfBirth", inner_name="placeOfBirth"
            ),
            nationalities=_texts_under(entry, "nationalityList", "nationality", "country"),
            title=child_text(entry, "title"),
            remarks=child_text(entry, "remarks"),
            vessel=vessel,
        )


def map_sdn_type(sdn_type: str | None) -> tuple[EntityKind | None, str | None]:
    """Map one sdnType text onto the stored kind, or onto the reason it is not stored.

    Aircraft are real entries this pipeline keeps out of the graph by choice,
    so they get their own reason. Any other unrecognized value, including a
    missing sdnType, is an unknown type.
    """
    match sdn_type:
        case "Individual":
            return EntityKind.PERSON, None
        case "Entity":
            return EntityKind.ORGANIZATION, None
        case "Vessel":
            return EntityKind.VESSEL, None
        case "Aircraft":
            return None, "aircraft_out_of_scope"
        case "Submarine":
            return None, "unknown_sdn_type"
        case None:
            return None, "unknown_sdn_type"
        case _:
            return None, "unknown_sdn_type"


def extract_addresses(entry: etree._Element) -> list[AddressField]:
    """Turn each address element under addressList into one AddressField.

    The publisher's original spellings are kept. stateOrProvince maps to
    region and postalCode to postal_code. A field the element omits stays "".
    """
    result: list[AddressField] = []
    for container in child_elements(entry, "addressList"):
        for address in child_elements(container, "address"):
            result.append(
                AddressField(
                    line1=child_text(address, "address") or "",
                    city=child_text(address, "city") or "",
                    region=child_text(address, "stateOrProvince") or "",
                    postal_code=child_text(address, "postalCode") or "",
                    country=child_text(address, "country") or "",
                )
            )
    return result


def extract_identifiers(
    entry: etree._Element, vessel: VesselInfo | None
) -> list[IdentifierField]:
    """Turn each id element under idList into one IdentifierField.

    A vessel registration id is also copied onto the VesselInfo of vessel
    records. The first one wins, and a vessel without any registration id
    keeps imo None. An id without an idCountry child keeps country None.
    """

    result = []
    for container in child_elements(entry, "idList"):
        for id_elem in child_elements(container, "id"):
            id_type = child_text(id_elem, "idType")
            number = child_text(id_elem, "idNumber")
            country = child_text(id_elem, "idCountry")

            if vessel is not None and id_type == VESSEL_REGISTRATION_ID_TYPE:
                if vessel.imo is None:
                    vessel.imo = number

            result.append(
                IdentifierField(id_type=id_type, number=number, country=country)
            )

    return result


def _display_name(entry: etree._Element, kind: EntityKind) -> str:
    """Assemble the display name the publisher itself would print.

    Individuals carry a firstName plus a lastName; every other kind puts the
    whole name in lastName. A missing firstName must not produce a leading
    space.
    """
    last = child_text(entry, "lastName") or ""
    if kind is EntityKind.PERSON:
        first = child_text(entry, "firstName")
        if first:
            return f"{first} {last}"
    return last


def _aliases(entry: etree._Element) -> list[str]:
    """One display string per aka element, in document order."""
    names: list[str] = []
    for container in child_elements(entry, "akaList"):
        for aka in child_elements(container, "aka"):
            first = child_text(aka, "firstName")
            last = child_text(aka, "lastName")
            if first and last:
                names.append(f"{first} {last}")
            elif last:
                names.append(last)
            elif first:
                names.append(first)
    return names


def _dates_of_birth(entry: etree._Element) -> list[PartialDate]:
    """Keep the raw date text and store the year only when the text states one."""
    dates: list[PartialDate] = []
    for container in child_elements(entry, "dateOfBirthList"):
        for birth in child_elements(container, "dateOfBirth"):
            raw = child_text(birth, "date")
            if raw is None:
                continue
            match = _YEAR_IN_TEXT.search(raw)
            dates.append(PartialDate(raw=raw, year=int(match.group(1)) if match else None))
    return dates


def _texts_under(
    entry: etree._Element,
    container_name: str,
    item_name: str,
    inner_name: str | None = None,
    last_inner_name: str | None = None,
) -> list[str]:
    """Collect the text of one named child under repeated list containers.

    OFAC wraps repeats as <XList><X>text</X></XListList>. nationalityList holds
    nationality elements whose text sits in a country child, so inner_name
    names the grandchild to read when the item itself has no direct text.
    """
    values: list[str] = []
    for container in child_elements(entry, container_name):
        for item in child_elements(container, item_name):
            if not last_inner_name:
                value = child_text(item, inner_name) if inner_name else item.text
                if value is not None:
                    value = value.strip()
                if value:
                    values.append(value)
            else:
                for last_item in item:
                    value = child_text(last_item, last_inner_name) if last_inner_name else last_item.text
                    if value is not None:
                        value = value.strip()
                    if value:
                        values.append(value)
    return values
