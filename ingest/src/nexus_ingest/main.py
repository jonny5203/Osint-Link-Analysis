"""Nexus ingest batch CLI (PLAN.md P1.4).

This is a batch command, not a long-running HTTP service. Phase 1 only requires
that `nexus-ingest --help` exits zero and lists the `source` and `resolve`
command groups; per-source and resolution commands are implemented in later
phases and raise NotImplementedError until then.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence


def _not_implemented(label: str) -> int:
    print(
        f"nexus-ingest: '{label}' is not implemented in this phase.",
        file=sys.stderr,
    )
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexus-ingest",
        description="Nexus OSINT sanctions ingestion and entity resolution (batch CLI).",
    )
    sub = parser.add_subparsers(dest="group", required=True, metavar="<command>")

    source = sub.add_parser(
        "source",
        help="Run a source ingestion pipeline (ofac, eu, un).",
    )
    source_sub = source.add_subparsers(dest="source_name", metavar="<source>")
    for name in ("ofac", "eu", "un"):
        sp = source_sub.add_parser(
            name, help=f"Run the {name.upper()} ingestion pipeline."
        )
        sp.set_defaults(func=lambda label=f"source {name}": _not_implemented(label))

    resolve = sub.add_parser(
        "resolve",
        help="Run entity resolution over ingested records.",
    )
    resolve.set_defaults(func=lambda: _not_implemented("resolve"))

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return func()


if __name__ == "__main__":
    raise SystemExit(main())
