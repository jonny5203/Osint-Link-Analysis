"""Unit tests for the source-neutral ingestion models."""

from __future__ import annotations

from nexus_ingest.models import (
    EntityKind,
    FetchResult,
    ImportReport,
    NormalizedRecord,
    ParseFailure,
    ParseStats,
    PartialDate,
    WriteStats,
)


def test_normalized_record_defaults_preserve_empty_not_none() -> None:
    record = NormalizedRecord(
        dataset_id="ofac-sdn",
        external_id="10001",
        kind=EntityKind.PERSON,
        display_name="Avery Fixture",
    )

    assert record.aliases == []
    assert record.addresses == []
    assert record.identifiers == []
    assert record.programs == []
    assert record.dates_of_birth == []
    assert record.record_hash is None


def test_partial_date_keeps_publisher_precision() -> None:
    partial = PartialDate(raw="1976")
    full = PartialDate(raw="18 Mar 1980", year=1980)

    assert partial.year is None
    assert full.year == 1980
    assert full.raw == "18 Mar 1980"


def test_entity_kind_values_match_java_contracts() -> None:
    assert [kind.value for kind in EntityKind] == [
        "PERSON",
        "ORGANIZATION",
        "VESSEL",
        "ADDRESS",
    ]


def test_parse_stas_do_not_reconcile_when_a_record_was_lost() -> None:
    stats = ParseStats(
        encountered=6,
        supported=3,
        unsupported_by_reason={"aircraft_out_of_scope": 1},
        failures=[ParseFailure(external_id=None, reason="missing_uid")],
    )

    assert not stats.reconciles()


def test_parse_stats_reconcile_when_every_record_counted() -> None:
    # Two aircraft records: len(unsupported_by_reason) counts 1 reason,
    # sum(values()) counts 2 records — only the test can tell the difference.
    stats = ParseStats(
        encountered=7,
        supported=4,
        unsupported_by_reason={"aircraft_out_of_scope": 2},
        failures=[ParseFailure(external_id=None, reason="missing_uid")],
    )

    assert stats.unsupported_total == 2
    assert stats.failed == 1
    assert stats.reconciles()


def test_fetch_result_covers_local_file_runs() -> None:
    fetch = FetchResult(
        dataset_id="ofac-sdn",
        byte_count=10,
        sha256="a" * 64,
        from_file=True,
    )

    assert fetch.requested_url is None
    assert fetch.status_code is None
    assert fetch.from_cache is False


def test_writes_stats_starts_at_zero() -> None:
    stats = WriteStats()

    assert (stats.inserted, stats.changed, stats.unchanged) == (0, 0, 0)
    assert (stats.failed, stats.deactivated) == (0, 0)


def test_import_report_marks_dry_runs_without_write_stats() -> None:
    report = ImportReport(
        run_id="ofac-sdn:20260824T100000Z:aaaaaaaaaaaa",
        dataset_id="ofac-sdn",
        mode="dry-run",
        status="succeeded",
        started_at="2026-08-24T10:00:00Z",
        finished_at="2026-08-24T10:00:05Z",
        fetch=FetchResult(dataset_id="ofac-sdn", byte_count=0, sha256="b" * 64),
        parse=ParseStats(encountered=0, supported=0),
    )

    assert report.write is None
    assert report.error is None
