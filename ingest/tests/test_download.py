"""Unit tests for the snapshot downloader. All HTTP is canned, never real."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from nexus_ingest.download import DownloadError, _host_allowed, fetch_snapshot
from nexus_ingest.source_config import SourceConfig

NOW = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
BODY = b"<sdnList><sdnEntry><uid>7</uid></sdnEntry></sdnList>"
BODY_SHA = hashlib.sha256(BODY).hexdigest()
XML_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
SLS_XML_URL = "https://sanctionslistservice.ofac.treas.gov/api/exports/sdn.xml"


def _config(**overrides) -> SourceConfig:
    values = dict(
        key="ofac",
        dataset_id="ofac-sdn",
        publisher="OFAC",
        landing_url="https://ofac.treasury.gov/sanctions-list-service",
        download_url=XML_URL,
        expected_root_local_name="sdnList",
        max_bytes=1000,
        timeout_seconds=5,
        allowed_redirect_hosts=(
            "www.treasury.gov",
            "sanctionslistservice.ofac.treas.gov",
        ),
        parser_format_version=1,
    )
    values.update(overrides)
    return SourceConfig(**values)


def _transport(
    routes: dict[str, httpx.Response], seen: list[str]
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return routes[str(request.url)]

    return httpx.MockTransport(handler)


def _refusing_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network touched when it should not be")

    return httpx.MockTransport(handler)


def test_host_rule_accepts_exact_and_subdomain_hosts() -> None:
    assert _host_allowed("treasury.gov", ("treasury.gov",))
    assert _host_allowed("www.treasury.gov", ("treasury.gov",))


def test_host_rule_rejects_lookalike_and_unrelated_hosts() -> None:
    allowed = ("www.treasury.gov",)
    assert not _host_allowed("evil-www.treasury.gov", allowed)
    assert not _host_allowed("treasury.gov.evil.example", allowed)
    assert not _host_allowed("www.treasury.gov.evil.example", allowed)
    assert not _host_allowed("example.com", allowed)


def test_direct_download_writes_snapshot_and_manifest(tmp_path: Path) -> None:
    seen: list[str] = []
    transport = _transport({XML_URL: httpx.Response(200, content=BODY)}, seen)
    root = tmp_path / "raw"

    result = fetch_snapshot(_config(), now=NOW, transport=transport, raw_root=root)

    assert result.from_cache is False
    assert result.from_file is False
    assert result.sha256 == BODY_SHA
    assert result.byte_count == len(BODY)
    assert result.status_code == 200
    assert result.snapshot_path == root / "ofac" / "20260830" / f"{BODY_SHA}.xml"
    assert result.snapshot_path.read_bytes() == BODY

    manifest = json.loads(result.snapshot_path.with_suffix(".json").read_text())
    assert manifest["sha256"] == BODY_SHA
    assert manifest["dataset_id"] == "ofac-sdn"
    assert manifest["requested_url"] == XML_URL
    assert manifest["retrieved_at"] == "2026-08-30T12:00:00Z"
    assert manifest["parser_format_version"] == 1


def test_redirect_chain_is_followed_and_recorded(tmp_path: Path) -> None:
    seen: list[str] = []
    transport = _transport(
        {
            XML_URL: httpx.Response(302, headers={"location": SLS_XML_URL}),
            SLS_XML_URL: httpx.Response(200, content=BODY),
        },
        seen,
    )

    result = fetch_snapshot(
        _config(), now=NOW, transport=transport, raw_root=tmp_path / "raw"
    )

    assert result.final_url == SLS_XML_URL
    assert result.sha256 == BODY_SHA
    assert seen == [XML_URL, SLS_XML_URL]


@pytest.mark.parametrize(
    "redirect_target",
    [
        "https://evil.example/sdn.xml",
        "https://evil-www.treasury.gov/sdn.xml",
        "http://sanctionslistservice.ofac.treas.gov/api/exports/sdn.xml",
    ],
)
def test_bad_redirect_is_refused_before_connecting(
    tmp_path: Path, redirect_target: str
) -> None:
    # All three targets are bad for different reasons: a stranger host, a
    # lookalike host, and an allowlisted host over cleartext http. In every
    # case the refusal must happen before any request to the target.
    seen: list[str] = []
    transport = _transport(
        {XML_URL: httpx.Response(302, headers={"location": redirect_target})}, seen
    )

    with pytest.raises(DownloadError):
        fetch_snapshot(
            _config(), now=NOW, transport=transport, raw_root=tmp_path / "raw"
        )

    assert seen == [XML_URL]


def test_html_error_page_is_rejected(tmp_path: Path) -> None:
    transport = _transport(
        {XML_URL: httpx.Response(200, content=b"<html><body>blocked</body></html>")},
        [],
    )

    with pytest.raises(DownloadError, match="HTML"):
        fetch_snapshot(
            _config(), now=NOW, transport=transport, raw_root=tmp_path / "raw"
        )


def test_html_detection_survives_whitespace_and_case(tmp_path: Path) -> None:
    transport = _transport(
        {XML_URL: httpx.Response(200, content=b"  \n<!DOCTYPE HTML><html>")},
        [],
    )

    with pytest.raises(DownloadError, match="HTML"):
        fetch_snapshot(
            _config(), now=NOW, transport=transport, raw_root=tmp_path / "raw"
        )


def test_download_over_the_byte_cap_is_rejected(tmp_path: Path) -> None:
    transport = _transport({XML_URL: httpx.Response(200, content=b"x" * 2001)}, [])

    with pytest.raises(DownloadError, match="cap"):
        fetch_snapshot(
            _config(max_bytes=2000),
            now=NOW,
            transport=transport,
            raw_root=tmp_path / "raw",
        )


def test_cached_snapshot_is_reused_without_network_and_force_bypasses_it(
    tmp_path: Path,
) -> None:
    day_dir = tmp_path / "raw" / "ofac" / "20260830"
    day_dir.mkdir(parents=True)
    snapshot = day_dir / f"{BODY_SHA}.xml"
    snapshot.write_bytes(BODY)
    manifest = {
        "sha256": BODY_SHA,
        "byte_count": len(BODY),
        "requested_url": XML_URL,
        "final_url": SLS_XML_URL,
        "status_code": 200,
        "retrieved_at": "2026-08-30T06:00:00Z",
    }
    snapshot.with_suffix(".json").write_text(json.dumps(manifest))

    cached = fetch_snapshot(
        _config(), now=NOW, transport=_refusing_transport(), raw_root=tmp_path / "raw"
    )
    assert cached.from_cache is True
    assert cached.snapshot_path == snapshot
    assert cached.final_url == SLS_XML_URL
    assert cached.sha256 == BODY_SHA

    forced = fetch_snapshot(
        _config(),
        now=NOW,
        force=True,
        transport=_transport({XML_URL: httpx.Response(200, content=BODY)}, []),
        raw_root=tmp_path / "raw",
    )
    assert forced.from_cache is False


def test_local_file_input_hashes_without_network_or_cache(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.xml"
    fixture.write_bytes(BODY)

    result = fetch_snapshot(
        _config(),
        now=NOW,
        source_file=fixture,
        transport=_refusing_transport(),
    )

    assert result.from_file is True
    assert result.from_cache is False
    assert result.sha256 == BODY_SHA
    assert result.byte_count == len(BODY)
    assert result.snapshot_path is None
