"""Unit tests for the snapshot downloader. All HTTP is canned, never real."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from nexus_ingest.download import (
    DownloadError,
    _host_allowed,
    _require_cache_integrity,
    _validate_snapshot_xml,
    fetch_snapshot,
)
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
    assert result.snapshot_path == fixture.resolve()


@pytest.mark.parametrize(
    "body",
    [
        b"<sdnList/>",
        b'<sdnList xmlns="urn:changed"/>',
        b'<s:sdnList xmlns:s="urn:changed"><s:sdnEntry/></s:sdnList>',
    ],
)
def test_snapshot_validation_accepts_root_local_name(
    tmp_path: Path, body: bytes
) -> None:
    snapshot = tmp_path / "source.xml"
    snapshot.write_bytes(body)

    assert _validate_snapshot_xml(_config(), snapshot) is None


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b" \n\t ",
        b"<unexpected/>",
        b"<sdnList><broken></sdnList>",
        b"<sdnList/>trailing-junk",
        b"<!DOCTYPE sdnList><sdnList/>",
        b'<!DOCTYPE sdnList [<!ENTITY name "expanded">]><sdnList>&name;</sdnList>',
        b'<!DOCTYPE sdnList SYSTEM "https://example.invalid/source.dtd"><sdnList/>',
    ],
)
def test_snapshot_validation_rejects_invalid_documents(
    tmp_path: Path, body: bytes
) -> None:
    snapshot = tmp_path / "source.xml"
    snapshot.write_bytes(body)

    with pytest.raises(DownloadError, match="ofac-sdn"):
        _validate_snapshot_xml(_config(), snapshot)


@pytest.mark.parametrize("entry_point", ["download", "cache", "file"])
def test_every_fetch_path_validates_the_whole_document(
    tmp_path: Path, entry_point: str
) -> None:
    body = b"<sdnList><sdnEntry/></sdnList>trailing-junk"
    root = tmp_path / "raw"
    source_file = None
    transport = _refusing_transport()
    if entry_point == "download":
        transport = _transport({XML_URL: httpx.Response(200, content=body)}, [])
    elif entry_point == "cache":
        snapshot = (
            root / "ofac" / "20260830" / f"{hashlib.sha256(body).hexdigest()}.xml"
        )
        snapshot.parent.mkdir(parents=True)
        snapshot.write_bytes(body)
    else:
        source_file = tmp_path / "input.xml"
        source_file.write_bytes(body)

    with pytest.raises(DownloadError, match="ofac-sdn"):
        fetch_snapshot(
            _config(),
            now=NOW,
            source_file=source_file,
            transport=transport,
            raw_root=root,
        )

    if entry_point == "download":
        assert list(root.rglob("*.xml")) == []
        assert list(root.rglob("*.json")) == []
        assert list(root.rglob(".partial-*")) == []


@pytest.mark.parametrize("manifest_body", [None, "not-json", "[]", "{}"])
def test_cache_without_usable_manifest_is_measured_and_validated(
    tmp_path: Path, manifest_body: str | None
) -> None:
    root = tmp_path / "raw"
    snapshot = root / "ofac" / "20260830" / f"{BODY_SHA}.xml"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(BODY)
    if manifest_body is not None:
        snapshot.with_suffix(".json").write_text(manifest_body)

    result = fetch_snapshot(
        _config(), now=NOW, transport=_refusing_transport(), raw_root=root
    )

    assert result.from_cache is True
    assert result.sha256 == BODY_SHA
    assert result.byte_count == len(BODY)
    assert result.final_url is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sha256", "0" * 64),
        ("sha256", None),
        ("byte_count", len(BODY) + 1),
        ("byte_count", str(len(BODY))),
        ("byte_count", float(len(BODY))),
        ("byte_count", True),
        ("dataset_id", "un-consolidated"),
        ("parser_format_version", 2),
        ("parser_format_version", "1"),
        ("parser_format_version", 1.0),
        ("parser_format_version", True),
    ],
)
def test_cache_integrity_rejects_conflicting_manifest_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    with pytest.raises(DownloadError) as error:
        _require_cache_integrity(
            _config(),
            tmp_path / f"{BODY_SHA}.xml",
            {field: value},
            byte_count=len(BODY),
            sha256=BODY_SHA,
        )
    assert "ofac-sdn" in str(error.value)
    assert field in str(error.value)


def test_cache_integrity_accepts_matching_manifest(tmp_path: Path) -> None:
    manifest = {
        "dataset_id": "ofac-sdn",
        "sha256": BODY_SHA,
        "byte_count": len(BODY),
        "parser_format_version": 1,
    }

    assert (
        _require_cache_integrity(
            _config(),
            tmp_path / f"{BODY_SHA}.xml",
            manifest,
            byte_count=len(BODY),
            sha256=BODY_SHA,
        )
        is None
    )


def test_cache_rejects_changed_bytes_under_old_digest(tmp_path: Path) -> None:
    root = tmp_path / "raw"
    snapshot = root / "ofac" / "20260830" / f"{BODY_SHA}.xml"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b"<sdnList/>")

    with pytest.raises(DownloadError, match="filename"):
        fetch_snapshot(
            _config(), now=NOW, transport=_refusing_transport(), raw_root=root
        )
    assert snapshot.read_bytes() == b"<sdnList/>"


def test_rejected_refresh_preserves_cache_and_removes_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "raw"
    snapshot = root / "ofac" / "20260830" / f"{BODY_SHA}.xml"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(BODY)
    manifest = snapshot.with_suffix(".json")
    manifest.write_text('{"sha256": "preserve-existing-metadata"}')
    previous_manifest = manifest.read_bytes()

    def reject_snapshot(config: SourceConfig, path: Path) -> None:
        assert config.dataset_id == "ofac-sdn"
        assert path.name.startswith(".partial-")
        assert path.read_bytes() == BODY
        raise DownloadError("ofac-sdn: rejected by validator")

    # Inject rejection to test publication/cleanup independently of XML parsing.
    monkeypatch.setattr("nexus_ingest.download._validate_snapshot_xml", reject_snapshot)
    with pytest.raises(DownloadError, match="rejected by validator"):
        fetch_snapshot(
            _config(),
            force=True,
            now=NOW,
            transport=_transport({XML_URL: httpx.Response(200, content=BODY)}, []),
            raw_root=root,
        )

    assert snapshot.read_bytes() == BODY
    assert manifest.read_bytes() == previous_manifest
    assert set(snapshot.parent.iterdir()) == {snapshot, manifest}


def test_oversized_local_file_fails_without_creating_cache(tmp_path: Path) -> None:
    source_file = tmp_path / "input.xml"
    source_file.write_bytes(BODY)
    root = tmp_path / "raw"

    with pytest.raises(DownloadError, match="cap"):
        fetch_snapshot(
            _config(max_bytes=len(BODY) - 1),
            source_file=source_file,
            transport=_refusing_transport(),
            raw_root=root,
        )

    assert not root.exists()


def test_cache_prefers_newest_snapshot_over_digest_order(tmp_path: Path) -> None:
    root = tmp_path / "raw"
    day_dir = root / "ofac" / "20260830"
    day_dir.mkdir(parents=True)
    bodies = [BODY, b"<sdnList/>"]
    snapshots = sorted((hashlib.sha256(body).hexdigest(), body) for body in bodies)
    # The newer file sorts first by digest, so choosing the last name is wrong.
    newest = None
    for index, (digest, body) in enumerate(snapshots):
        snapshot = day_dir / f"{digest}.xml"
        snapshot.write_bytes(body)
        timestamp = 200 - index * 100
        os.utime(snapshot, (timestamp, timestamp))
        if index == 0:
            newest = snapshot

    result = fetch_snapshot(
        _config(), now=NOW, transport=_refusing_transport(), raw_root=root
    )

    assert result.from_cache is True
    assert result.snapshot_path == newest
    assert result.sha256 == newest.stem
