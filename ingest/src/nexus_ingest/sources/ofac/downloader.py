"""Download the OFAC consolidated SDN list (PLAN.md T3.2)."""

from __future__ import annotations

from pathlib import Path

SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"  # verify URL is current at start of T3


def download_sdn(force: bool = False) -> Path:
    """HTTP GET the SDN XML via httpx, cache under data/raw/ofac/<date>/sdn.xml.

    If today's file already exists and force=False, return the cached path.
    """
    raise NotImplementedError("T3.2")
