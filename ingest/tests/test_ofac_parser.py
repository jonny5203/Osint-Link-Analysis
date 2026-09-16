"""OFAC parser tests over fictional SDN-schema fixtures, never live data."""

from __future__ import annotations

from pathlib import Path

from nexus_ingest.models import (
    AddressField,
    EntityKind,
    NormalizedRecord,
    ParseStats,
)
from nexus_ingest.sources.ofac.parser import parse_sdn

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ofac"


def _parse_fixture(name: str) -> tuple[list[NormalizedRecord], ParseStats]:
    stats = ParseStats()
    records = list(parse_sdn(FIXTURE_DIR / name, stats, dataset_id="ofac-sdn"))
    return records, stats


def test_happy_fixture_reconciles_every_entry() -> None:
    records, stats = _parse_fixture("sdn_happy.xml")

    assert stats.encountered == 6
    assert stats.supported == 5
    assert stats.unsupported_by_reason == {"aircraft_out_of_scope": 1}
    assert stats.failed == 0
    assert stats.reconciles()
    assert len(records) == 5


def test_individual_keeps_original_spellings() -> None:
    records, _ = _parse_fixture("sdn_happy.xml")
    avery = next(r for r in records if r.external_id == "10001")

    assert avery.kind is EntityKind.PERSON
    assert avery.display_name == "Avery DER BERG"
    assert avery.aliases == ["Avery DERBERG"]
    assert avery.programs == ["PROGRAM ALPHA", "PROGRAM BETA"]
    assert [d.raw for d in avery.dates_of_birth] == ["18 Mar 1980", "1976"]
    assert avery.dates_of_birth[0].year == 1980
    assert avery.dates_of_birth[1].year == 1976
    assert avery.nationalities == ["Norway"]
    assert avery.places_of_birth == ["Portville"]
    assert avery.title == "Chief Executive"
    assert avery.remarks == "Provided false passport 2024."
    assert avery.identifiers[0].id_type == "Passport"
    assert avery.identifiers[0].number == "P1234567"
    assert avery.addresses == [
        AddressField(line1="1 Harbour Rd", city="Portville", country="Norway")
    ]


def test_entity_address_maps_postal_and_state_fields() -> None:
    records, _ = _parse_fixture("sdn_happy.xml")
    aurora = next(r for r in records if r.external_id == "20001")

    assert aurora.addresses[0].postal_code == "1000"
    assert aurora.addresses[0].line1 == "2 Quay St"


def test_entity_with_no_optional_fields_still_parses() -> None:
    records, _ = _parse_fixture("sdn_happy.xml")
    minimal = next(r for r in records if r.external_id == "50001")

    assert minimal.kind is EntityKind.ORGANIZATION
    assert minimal.display_name == "MINIMAL HOLDING SA"
    assert minimal.aliases == []
    assert minimal.addresses == []
    assert minimal.identifiers == []


def test_individual_without_first_name_uses_last_name_alone() -> None:
    records, _ = _parse_fixture("sdn_happy.xml")
    meridian = next(r for r in records if r.external_id == "60001")

    assert meridian.display_name == "MERIDIAN"


def test_vessel_registration_identifier_becomes_imo() -> None:
    records, _ = _parse_fixture("sdn_happy.xml")
    aurora = next(r for r in records if r.external_id == "30001")

    assert aurora.kind is EntityKind.VESSEL
    assert aurora.vessel is not None
    assert aurora.vessel.imo == "9990001"
    assert aurora.identifiers[0].id_type == "Vessel Registration Identification"


def test_changed_namespace_produces_the_same_counts() -> None:
    records, stats = _parse_fixture("sdn_namespace_changed.xml")

    assert stats.encountered == 3
    assert stats.supported == 2
    assert stats.unsupported_by_reason == {"aircraft_out_of_scope": 1}
    assert stats.failed == 0
    assert stats.reconciles()
    assert [r.external_id for r in records] == ["11001", "13001"]


def test_entry_without_uid_fails_the_record_not_the_file() -> None:
    records, stats = _parse_fixture("sdn_malformed.xml")

    assert stats.encountered == 3
    assert stats.supported == 1
    assert stats.unsupported_by_reason == {"aircraft_out_of_scope": 1}
    assert stats.failed == 1
    assert stats.failures[0].external_id is None
    assert stats.failures[0].reason == "missing_uid"
    assert stats.reconciles()
    assert [r.external_id for r in records] == ["21001"]


def test_records_reach_the_pipeline_unhashed() -> None:
    records, _ = _parse_fixture("sdn_happy.xml")

    assert all(record.record_hash is None for record in records)
