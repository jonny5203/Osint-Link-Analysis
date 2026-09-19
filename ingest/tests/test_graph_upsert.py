"""Unit tests for graph_upsert validation and id composition, with no database."""

from __future__ import annotations

import pytest

from nexus_ingest.graph_upsert import (
    WriteError,
    address_node_id,
    build_upsert_rows,
    entity_node_id,
    source_record_id,
    write_import,
)
from nexus_ingest.models import AddressField, EntityKind, NormalizedRecord


def _hashed_record(**overrides) -> NormalizedRecord:
    values = dict(
        dataset_id="ofac-sdn",
        external_id="10001",
        kind=EntityKind.PERSON,
        display_name="Avery DER BERG",
        record_hash="a" * 64,
        addresses=[AddressField(line1="1 Harbour Rd", city="Portville", country="Norway")],
    )
    values.update(overrides)
    return NormalizedRecord(**values)


class _RefusingDriver:
    """Any session use means validation failed to run first."""

    def session(self):
        raise AssertionError("the database must not be touched by this test")


def test_ids_are_source_qualified_and_indexed() -> None:
    assert source_record_id("ofac-sdn", "10001") == "ofac-sdn:10001"
    assert entity_node_id("ofac-sdn:10001") == "entity:ofac-sdn:10001"
    assert address_node_id("ofac-sdn:10001", 0) == "address:ofac-sdn:10001:0"


def test_unhashed_records_are_refused_before_any_write() -> None:
    record = _hashed_record(record_hash=None)

    with pytest.raises(WriteError, match="10001"):
        write_import(
            _RefusingDriver(),
            config=None,
            records=[record],
            run_id="ofac-sdn:20260916T120000Z:aaaaaaaaaaaa",
            started_at="2026-09-16T12:00:00Z",
            fetch=None,
        )


def test_kind_without_allowlisted_label_is_refused() -> None:
    record = _hashed_record(kind=EntityKind.ADDRESS)

    with pytest.raises(WriteError, match="ADDRESS"):
        write_import(
            _RefusingDriver(),
            config=None,
            records=[record],
            run_id="ofac-sdn:20260916T120000Z:aaaaaaaaaaaa",
            started_at="2026-09-16T12:00:00Z",
            fetch=None,
        )


def test_rows_are_grouped_by_allowlisted_label() -> None:
    person = _hashed_record()
    vessel = _hashed_record(
        external_id="30001",
        kind=EntityKind.VESSEL,
        display_name="AURORA",
    )

    rows = build_upsert_rows([person, vessel])

    assert list(rows) == ["Person", "Vessel"]
    assert rows["Person"][0]["sr_id"] == "ofac-sdn:10001"
    assert rows["Vessel"][0]["entity_id"] == "entity:ofac-sdn:30001"


def test_rows_carry_original_and_derived_values() -> None:
    record = _hashed_record()

    row = build_upsert_rows([record])["Person"][0]

    assert row["display_name"] == "Avery DER BERG"
    assert row["normalized_name"] == "avery der berg"
    assert row["addresses"][0]["id"] == "address:ofac-sdn:10001:0"
    assert row["addresses"][0]["normalized_address"] == "1 harbour rd, portville, norway"
