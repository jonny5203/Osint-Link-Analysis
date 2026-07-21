"""OFAC pipeline CLI (PLAN.md T3.7).

Run with:  python -m nexus_ingest.sources.ofac.cli
Wires downloader -> parser -> mapper -> upsert and prints UpsertStats.
Must be idempotent: re-running with today's data reports inserted=0.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("T3.7")


if __name__ == "__main__":
    main()
