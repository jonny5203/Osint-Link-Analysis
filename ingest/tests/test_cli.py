from __future__ import annotations

import subprocess
import sys


def test_help_lists_batch_command_groups() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "nexus_ingest.main", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "source" in result.stdout
    assert "resolve" in result.stdout


def test_unimplented_source_command_fails_clearly() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "nexus_ingest.main", "source", "ofac"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "not implemented in this phase" in result.stderr
