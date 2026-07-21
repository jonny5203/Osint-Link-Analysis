"""Pair scoring for entity resolution (PLAN.md T6.2).

Pure functions — trivial to unit test. Compute each signal in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PairScore:
    name_score: float  # rapidfuzz token_sort_ratio
    jw_score: float  # Jaro-Winkler
    dob_match: bool
    country_match: bool
    address_score: float  # rapidfuzz on raw address string


def score_pair(a, b) -> PairScore:
    raise NotImplementedError("T6.2")
