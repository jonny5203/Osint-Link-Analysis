"""Load per source settings from config/sources.toml.

URLs, limits, and allowed redirect hosts are configuration data, not constants scarreted
through the code. Two names identify one source on purpose, the [source.<key>] table name is what the CLI
accepts (`nexus-ingest source run ofac`), while dataset_id is the stable graph identity (Dataset {id: "ofac-sdn"})
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class UnknownSourceError(KeyError):
    """The CLI named a source that has no [source.<key>] table."""


class SourceConfigError(ValueError):
    """A source table exists but is malformed or incomplete"""


@dataclass(frozen=True)
class SourceConfig:
    """Validated setttings for one sanctions source."""

    key: str
    dataset_id: str
    publisher: str
    landing_url: str
    download_url: str
    expected_root_local_name: str
    max_bytes: int
    timeout_seconds: int
    allowed_redirect_hosts: tuple[str, ...]
    parser_format_version: int


def default_config_path() -> Path:
    """ingest/config/sources.toml, located relative to this file.

    uv installs the package editable, so __file__ stays inside the repo at ingest/src/nexus_ingest/ and
    parent[2] is the ingest/ directory. Editing the TOML therefore never requires reinstalling.
    """

    return Path(__file__).resolve().parents[2] / "config" / "sources.toml"


def load_source_config(key: str, config_path: Path | None = None) -> SourceConfig:
    """Read, validate, and return the settings table for key.

    Validation happens here, at load time, so a broken table fails before any network or database work, never mid-import.
    """

    path = config_path if config_path is not None else default_config_path()
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    version = data.get("version")
    if version != 1:
        raise SourceConfigError(f"{path}: expected version 1, got {version!r}")

    sources = data.get("sources")
    if not isinstance(sources, dict) or key not in sources:
        known = sorted(sources) if isinstance(sources, dict) else []
        raise UnknownSourceError(f"{path}: no [sources.{key}] table; known: {known}")

    table = sources[key]

    text_values: dict[str, str] = {}
    for field_name in (
        "dataset_id",
        "publisher",
        "landing_url",
        "download_url",
        "expected_root_local_name",
    ):
        value = table.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise SourceConfigError(
                f"[sources.{key}]: {field_name} must be a non-empty string"
            )
        text_values[field_name] = value

    int_values: dict[str, int] = {}
    for field_name in ("max_bytes", "timeout_seconds", "parser_format_version"):
        value = table.get(field_name)

        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SourceConfigError(
                f"[sources.{key}]: {field_name} must be a positive integer"
            )
        int_values[field_name] = value

    hosts_raw = table.get("allowed_redirect_hosts")
    if not isinstance(hosts_raw, list) or not hosts_raw:
        raise SourceConfigError(
            f"[sources.{key}]: allowed_redirect_hosts must be a non-empty list"
        )
    hosts = tuple(_clean_host(host, key) for host in hosts_raw)

    return SourceConfig(
        key=key,
        dataset_id=text_values["dataset_id"],
        publisher=text_values["publisher"],
        landing_url=text_values["landing_url"],
        download_url=text_values["download_url"],
        expected_root_local_name=text_values["expected_root_local_name"],
        max_bytes=int_values["max_bytes"],
        timeout_seconds=int_values["timeout_seconds"],
        allowed_redirect_hosts=hosts,
        parser_format_version=int_values["parser_format_version"],
    )


def _clean_host(host: object, key: str) -> str:
    """Normalize one allowlist entry, rejecting anything URL-shaped.

    Redirect checks compare bare host names only, so an entry that still
    carries a scheme or path would silently never match.
    """
    if not isinstance(host, str):
        raise SourceConfigError(f"[sources.{key}]: allowlist entries must be strings")
    cleaned = host.strip().lower()
    if not cleaned or "://" in cleaned or "/" in cleaned:
        raise SourceConfigError(
            f"[sources.{key}]: allowlist entry {host!r} must be a bare host name"
        )
    return cleaned
