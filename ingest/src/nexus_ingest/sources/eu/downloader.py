"""Download the EU consolidated list (PLAN.md T4.2)."""

from __future__ import annotations

from pathlib import Path

# TODO(T4.2): confirm the current EU consolidated list URL — it moves.
EU_LIST_URL = "TODO"


def download_eu(force: bool = False) -> Path:
    raise NotImplementedError("T4.2")
