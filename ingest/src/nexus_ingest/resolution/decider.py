"""The decision function for entity resolution (PLAN.md T6.5).

This is the one piece of meaningful judgment code in the project — YOU implement it.
See PLAN.md T6.5 for the trade-offs (name-score danger, DOB/country signals, the LINK
middle band, and how the choice interacts with design decision D1).
"""

from __future__ import annotations

from enum import Enum

from nexus_ingest.resolution.scorer import PairScore


class Decision(Enum):
    MERGE = "merge"
    LINK = "link"
    SKIP = "skip"


def decide(score: PairScore) -> Decision:
    """
    Return one of: Decision.MERGE, Decision.LINK, Decision.SKIP.
    - MERGE: high confidence these are the same entity
    - LINK:  probably the same, but defer to analyst review
    - SKIP:  distinct entities
    """
    # TODO(you): implement the decision logic
    raise NotImplementedError("T6.5")
