"""Blocking for entity resolution (PLAN.md T6.1).

Block key = first 3 chars of normalized surname + country (or None).
Normalize: lowercase, strip punctuation, transliterate Cyrillic->Latin.
"""

from __future__ import annotations

BlockKey = tuple[str, str | None]


def block(entities) -> dict[BlockKey, list]:
    raise NotImplementedError("T6.1")
