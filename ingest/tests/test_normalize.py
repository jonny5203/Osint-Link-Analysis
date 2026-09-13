"""Unit tests for deterministic normalization and record hashing."""

from __future__ import annotations

from nexus_ingest.models import (
    AddressField,
    EntityKind,
    IdentifierField,
    NormalizedRecord,
    PartialDate,
    VesselInfo,
)
from nexus_ingest.normalize import (
    collapse_whitespace,
    compute_record_hash,
    normalize_address,
    normalize_text
)


def _sample_record(**overrides) -> NormalizedRecord:
    """One fully populated fictional record; tests override single fields."""
    values = dict(
        dataset_id="ofac-sdn",
        external_id="10001",
        kind=EntityKind.PERSON,
        display_name="Avery Der Berg",
        aliases=["A. Der Berg", "Derberg, Avery"],
        addresses=[
            AddressField(line1="1 Harbour Rd", city="Portville", country="Norway"),
        ],
        identifiers=[IdentifierField(id_type="Passport", number="P1234567", country="Norway")],
        programs=["TABLE ONE", "TABLE TWO"],
        dates_of_birth=[PartialDate(raw="18 Mar 1980", year=1980)],
        places_of_birth=["Portville"],
        nationalities=["Norwegian"],
        title="Chief Executive",
        remarks="Provided false passport 2024.",
        vessel=None,
    )
    values.update(overrides)
    return NormalizedRecord(**values)


def test_collapse_whitespace_shrinks_runs_and_trims() -> None:
    assert collapse_whitespace("  Van   der\tBerg ") == "Van der Berg"
    assert collapse_whitespace("") == ""
    assert collapse_whitespace("   x ") == "x"


def test_normalize_address_joins_only_the_fields_the_publisher_wrote() -> None:
    sparse = AddressField(line1="1 Harbour Rd", city="Portville", country="Norway")

    assert normalize_address(sparse) == "1 harbour rd, portville, norway"


def test_punctuation_separates_words_and_inner_whitespace_collapses() -> None:
    # Two spellings of the same name must land on one value, and neither on the
    # value of a name that lost its word boundary.
    joined = normalize_text("O'BRIEN")

    assert joined == normalize_text("O BRIEN")
    assert joined != normalize_text("OBRIEN")

    # Ligature folding, a dash, and a doubled inner space in one string.
    assert normalize_text("  ﬁrst–floor  SUITE ") == "first floor suite"


def test_identical_records_hash_identically() -> None:
    left = _sample_record()
    right = _sample_record()

    assert compute_record_hash(left) == compute_record_hash(right)
    assert len(compute_record_hash(left)) == 64


def test_content_change_changes_the_hash() -> None:
    original = _sample_record()
    renamed_alias = _sample_record(aliases=["A. Der Berg", "Totally Different Alias"])

    assert compute_record_hash(original) != compute_record_hash(renamed_alias)


def test_list_order_does_not_change_the_hash() -> None:
    # The parser meets aliases and addresses in document order, which can differ
    # between two snapshots of the same record with identical content.
    forward = _sample_record()
    backward = _sample_record(
        aliases=["Derberg, Avery", "A. Der Berg"],
        addresses=[
            AddressField(line1="1 Harbour Rd", city="Portville", country="Norway"),
            AddressField(line1="2 Quay St", city="Portville", country="Norway"),
        ],
    )
    # ...but forward's address list has only one entry while backward has two, so give
    # forward the same two addresses in reverse order before comparing the hashes.
    forward.addresses = list(reversed(backward.addresses))

    assert compute_record_hash(forward) == compute_record_hash(backward)


def test_empty_means_absent_when_hashing() -> None:
    # Same record content: one written with None, one with explicit empty values.
    silent = _sample_record(title=None, remarks=None, vessel=None)
    loud = _sample_record(title="", remarks="", vessel=VesselInfo())

    assert compute_record_hash(silent) == compute_record_hash(loud)


def test_unknown_kind_support_comes_from_the_models_not_the_hash() -> None:
    # The str-Enum must reach the hash payload as its plain value; this pins the
    # serialization the Neo4j driver and the Java enum both expect.
    enum = _sample_record(kind=EntityKind.VESSEL, vessel=VesselInfo(imo="9990001"))
    string = _sample_record(kind="VESSEL", vessel=VesselInfo(imo="9990001"))

    assert compute_record_hash(enum) == compute_record_hash(string)