"""Unit test for sources.toml loading"""

from __future__ import annotations

import pytest

from nexus_ingest.source_config import (
    SourceConfigError,
    UnknownSourceError,
    load_source_config,
)

_VALID_TABLE = """\
version = 1

[sources.ofac]
dataset_id = "ofac-sdn"
publisher = "OFAC"
landing_url = "https://ofac.treasury.gov/sanctions-list-service"
download_url = "https://www.treasury.gov/ofac/downloads/sdn.xml"
expected_root_local_name = "sdnList"
max_bytes = 1000
timeout_seconds = 5
parser_format_version = 1
allowed_redirect_hosts = ["www.treasury.gov"]
"""


def _write_config(tmp_path, body: str):
    path = tmp_path / "sources.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_committed_ofac_table_loads_with_expected_identity() -> None:
    config = load_source_config("ofac")

    assert config.key == "ofac"
    assert config.dataset_id == "ofac-sdn"
    assert config.expected_root_local_name == "sdnList"
    assert config.download_url.startswith("https://")
    assert config.max_bytes > 0
    assert config.timeout_seconds > 0
    assert config.parser_format_version == 1


def test_redirect_allowlist_covers_the_verified_hop_chain() -> None:
    config = load_source_config("ofac")

    assert "www.treasury.gov" in config.allowed_redirect_hosts
    assert "sanctionslistservice.ofac.treas.gov" in config.allowed_redirect_hosts


def test_unknown_source_raises() -> None:
    with pytest.raises(UnknownSourceError):
        load_source_config("does-not-exist")


def test_wrong_config_version_is_rejected(tmp_path) -> None:
    path = _write_config(tmp_path, _VALID_TABLE.replace("version = 1", "version = 2"))

    with pytest.raises(SourceConfigError, match="version"):
        load_source_config("ofac", config_path=path)


def test_missing_required_field_is_rejected(tmp_path) -> None:
    body = _VALID_TABLE.replace(
        'download_url = "https://www.treasury.gov/ofac/downloads/sdn.xml"\n', ""
    )
    path = _write_config(tmp_path, body)

    with pytest.raises(SourceConfigError, match="download_url"):
        load_source_config("ofac", config_path=path)


def test_url_shaped_allowlist_entry_is_rejected(tmp_path) -> None:
    # An entry with a scheme or path could never match a bare host, so the
    # loader refuses it instead of letting every download fail later.
    body = _VALID_TABLE.replace(
        'allowed_redirect_hosts = ["www.treasury.gov"]',
        'allowed_redirect_hosts = ["https://www.treasury.gov/ofac"]',
    )
    path = _write_config(tmp_path, body)

    with pytest.raises(SourceConfigError, match="bare host"):
        load_source_config("ofac", config_path=path)


def test_host_entries_are_normalized_to_lowercase(tmp_path) -> None:
    body = _VALID_TABLE.replace(
        'allowed_redirect_hosts = ["www.treasury.gov"]',
        'allowed_redirect_hosts = ["WWW.Treasury.GOV"]',
    )
    path = _write_config(tmp_path, body)

    config = load_source_config("ofac", config_path=path)

    assert config.allowed_redirect_hosts == ("www.treasury.gov",)


def test_boolean_is_not_a_positive_integer(tmp_path) -> None:
    # bool subclasses int in Python; the loader must reject `true` explicitly.
    body = _VALID_TABLE.replace("timeout_seconds = 5", "timeout_seconds = true")
    path = _write_config(tmp_path, body)

    with pytest.raises(SourceConfigError, match="timeout_seconds"):
        load_source_config("ofac", config_path=path)
