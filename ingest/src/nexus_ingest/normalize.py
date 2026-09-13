"""Deterministic comparison values for ingested records.

Three jobs, in the order the pipeline meets them:

-   normalize_text() turns any publisher string into a comparison form that survives
    cosmetic changes: full-width vs ASCII characters, capitalization, stray punctuation,
    doubled spaces. The original spelling is never overwritten; the graph stores both
    (display_name next to normalized_name).
-   normalize_address() does the same for the six address fields, joined into one line
    so an Entity:Address node has a single comparable value (normalized_address).
-   compute_record_hash() fingerprints the content of a NormalizedRecord. The writer
    compares this fingerprint against the one stored on the SourceRecord node to decide
    inserted / changed / unchanged, so the fingerprint must be stable: the same content
    must always produce the same hash even when the parser met the fields in a different
    order, and any real content change must produce a different hash.

The hash deliberately covers only what the publisher wrote, never anything
normalize_text() derives. If a normalization rule improves later, every stored record
must not flip to "changed" on the next import just because the comparison form moved.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from unicodedata import category
from dataclasses import asdict


from nexus_ingest.models import AddressField, EntityKind, NormalizedRecord

_WHITESPACE_RUN = re.compile(r"\s+")


def collapse_whitespace(text: str) -> str:
    """Trim the ends and shrink every run of whitespace to one plain space.

    "  Van   der  Berg " and "Van der Berg" must reach the same value. This runs
    last in every normalization chain, after earlier steps may have produced
    irregular spacing.
    """
    return _WHITESPACE_RUN.sub(" ", text).strip()


def normalize_text(text: str) -> str:
    """Return the comparison form of one publisher string.

    Two spellings that differ only cosmetically fold onto the same value, so
    matching survives publisher quirks. NFKC runs first: it replaces characters
    that only look different, so the ligature "ﬁ" becomes "fi" and the "№" sign
    becomes the letters "no". casefold runs next: it is stronger than lower(),
    folding "Straße" and "STRASSE" onto one value, which lower() never does.
    Every punctuation, symbol, and control character then becomes a space, so a
    separator keeps words apart instead of gluing them: "O'BRIEN" and "O BRIEN"
    fold to the same value, and neither matches "OBRIEN". The original string is
    never changed; the graph stores display_name beside this derived value.
    Empty or whitespace-only input returns "".
    """

    text_norm = unicodedata.normalize("NFKC", text)
    text_norm = text_norm.casefold()
    text_norm = text_norm.strip()

    result = ""
    for index, char in enumerate(text_norm):
        if char == " ":
            if text_norm[index + 1] == " ":
                continue
            if is_special(text_norm[index + 1]):
                continue

        if is_special(char):
            if index < (len(text_norm) - 1):
                if text_norm[index + 1] == " ":
                    continue
                if is_special(text_norm[index + 1]):
                    continue
            result = result + " "
        else:
            result = result + char

    result = result.strip()

    return result


def is_special(ch: str) -> bool:
    return category(ch).startswith(("P", "S", "Cc"))


def normalize_address(address: AddressField) -> str:
    """Return one comparable line for a postal address.

    The six fields are joined with ", " so the whole address can live in the single
    normalized_address property the graph contract gives Entity:Address nodes. Fields
    the publisher left empty drop out entirely, so an address with no region does not
    end in a dangling separator.
    """
    parts = [
        normalize_text(part)
        for part in (
            address.line1,
            address.line2,
            address.city,
            address.region,
            address.postal_code,
            address.country,
        )
        if part
    ]
    return ", ".join(parts)


def _canonical_dict(record: NormalizedRecord) -> dict:
    """Project a record onto a JSON-ready dict whose bytes never depend on chance.

    This projection is the entire idempotency guarantee for the writer: re-importing
    the same snapshot must produce byte-identical JSON here, or every record would be
    miscounted as "changed". Three rules make that true, applied by
    _prune_and_order():

    -   record_hash never enters the output, or the hash would depend on itself.
    -   "empty means absent": None, "", [], and {} drop out at every depth, so a
        parser writing title="" and one omitting the field describe the same record.
    -   every list comes out sorted by its canonical JSON form, so the order the
        parser happened to meet elements in cannot reach the bytes.

    dataset_id and external_id stay in: they are part of what the record says, and
    keeping them is one rule fewer to maintain.
    """
    canonical = asdict(record)
    canonical.pop("record_hash")
    # EntityKind normally arrives as an enum, but callers may pass the plain string;
    # both must reach the payload as the bare value ("PERSON").
    canonical["kind"] = (
        record.kind.value if isinstance(record.kind, EntityKind) else str(record.kind)
    )
    return _prune_and_order(canonical)


def _prune_and_order(value):
    """Apply the empty-means-absent and stable-order rules recursively."""
    if isinstance(value, dict):
        kept = {key: _prune_and_order(item) for key, item in value.items()}
        return {key: item for key, item in kept.items() if item not in (None, "", [], {})}
    if isinstance(value, list):
        kept = [_prune_and_order(item) for item in value]
        kept = [item for item in kept if item not in (None, "", [], {})]
        # Sorting the canonical JSON text gives any shape a total order without
        # per-list sort keys, and keeps one identical rule for strings and dicts.
        return sorted(
            kept,
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
        )
    return value


def compute_record_hash(record: NormalizedRecord) -> str:
    """Hash the canonical projection of a record into a 64-character hex string.

    Sorted keys make the JSON bytes independent of field order; the projection from
    _canonical_dict() already made list order and emptiness deterministic. sha256 is
    the same digest the raw download uses, so one algorithm covers both layers.
    """
    payload = json.dumps(
        _canonical_dict(record),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
