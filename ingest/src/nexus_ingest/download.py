"""Download a source snapshot into a cache with provenance manifests.

Everything here works for any source. Settings come from SourceConfig in
source_config.py. The result is a FetchResult from models.py. Snapshots
live under data/raw/<key>/<date>/, one folder per source per day.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from nexus_ingest.models import FetchResult
from nexus_ingest.source_config import SourceConfig

NEXUS_USER_AGENT = "nexus-ingest/0.1 (local OSINT demo)"
CHUNK_SIZE = 64 * 1024
MAX_REDIRECT_HOPS = 5


class DownloadError(RuntimeError):
    """The snapshot could not be retrieved. The message says why."""


def default_raw_root() -> Path:
    """ingest/data/raw, found relative to this file. parents[2] is ingest/."""
    return Path(__file__).resolve().parents[2] / "data" / "raw"


def fetch_snapshot(
    config: SourceConfig,
    *,
    force: bool = False,
    source_file: Path | None = None,
    now: datetime | None = None,
    transport: httpx.BaseTransport | None = None,
    raw_root: Path | None = None,
) -> FetchResult:
    """Return the raw bytes for one import, by file, cache, or network.

    An explicit --file input wins over everything. Next comes today's
    cached snapshot, unless force=True. Otherwise we download. The tests
    pass now and transport so they can pin the clock and serve canned
    responses instead of touching the network.
    """
    moment = now if now is not None else datetime.now(timezone.utc)
    root = raw_root if raw_root is not None else default_raw_root()

    if source_file is not None:
        return _snapshot_from_file(config, source_file)

    if not force:
        cached = _find_cached_snapshot(config, moment, root)
        if cached is not None:
            return cached

    return _download_to_cache(config, moment, root, transport)


def _snapshot_from_file(config: SourceConfig, source_file: Path) -> FetchResult:
    """Hash an existing local file. No cache copy, no manifest, no network."""
    hasher = hashlib.sha256()
    byte_count = 0
    with source_file.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            hasher.update(chunk)
            byte_count += len(chunk)
    if byte_count > config.max_bytes:
        raise DownloadError(
            f"{source_file} is {byte_count} bytes, over the {config.max_bytes} cap"
        )
    return FetchResult(
        dataset_id=config.dataset_id,
        byte_count=byte_count,
        sha256=hasher.hexdigest(),
        from_file=True,
    )


def _find_cached_snapshot(
    config: SourceConfig, moment: datetime, root: Path
) -> FetchResult | None:
    """Reuse today's snapshot when one exists, without touching the network.

    We cannot look a file up by its hash before downloading it. The hash is
    only known once the bytes have arrived. So the rule is one download per
    source per day, and force=True to bypass it within the same day.
    """
    day_dir = root / config.key / moment.strftime("%Y%m%d")
    snapshots = sorted(day_dir.glob("*.xml"))
    if not snapshots:
        return None
    # Hex names sort deterministically, so "the" snapshot of a day is stable.
    snapshot = snapshots[-1]
    manifest = _load_manifest(snapshot.with_suffix(".json")) or {}
    return FetchResult(
        dataset_id=config.dataset_id,
        byte_count=manifest.get("byte_count", snapshot.stat().st_size),
        sha256=snapshot.stem,
        snapshot_path=snapshot,
        requested_url=manifest.get("requested_url"),
        final_url=manifest.get("final_url"),
        status_code=manifest.get("status_code"),
        content_type=manifest.get("content_type"),
        from_cache=True,
    )


def _download_to_cache(
    config: SourceConfig,
    moment: datetime,
    root: Path,
    transport: httpx.BaseTransport | None,
) -> FetchResult:
    """Stream the snapshot to a temp file, hash it, then move it into place.

    Redirects are followed one hop at a time. Before each hop, the next
    host is checked against the allowlist. We connect only to hosts that
    pass, over https only. A response hook cannot do this. By the time a
    hook runs, the request to the unvetted host has already been sent.
    """
    requested_url = config.download_url
    _require_allowed_https(requested_url, config.allowed_redirect_hosts)

    hasher = hashlib.sha256()
    byte_count = 0
    final_url = requested_url
    status_code: int | None = None
    content_type: str | None = None
    day_dir = root / config.key / moment.strftime("%Y%m%d")

    with httpx.Client(
        follow_redirects=False,
        timeout=config.timeout_seconds,
        transport=transport,
    ) as client:
        url = requested_url
        # range gives us MAX_REDIRECT_HOPS + 1 attempts. Each redirect burns
        # one attempt and continues. A final response breaks out. If the
        # range runs out, every attempt was a redirect and the for-else
        # raises: the chain is longer than we allow.
        for _hop in range(MAX_REDIRECT_HOPS + 1):
            with client.stream(
                "GET", url, headers={"User-Agent": NEXUS_USER_AGENT}
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise DownloadError(
                            f"{url} redirected without a Location header"
                        )
                    next_url = httpx.URL(str(response.url)).join(location)
                    _require_allowed_https(str(next_url), config.allowed_redirect_hosts)
                    url = str(next_url)
                    continue
                if response.status_code != 200:
                    raise DownloadError(f"{url} returned HTTP {response.status_code}")

                final_url = str(response.url)
                status_code = response.status_code
                content_type = response.headers.get("content-type")
                day_dir.mkdir(parents=True, exist_ok=True)
                temp_path = day_dir / f".partial-{uuid.uuid4().hex}"

                try:
                    first_chunk = True
                    with temp_path.open("wb") as sink:
                        for chunk in response.iter_bytes():
                            if first_chunk:
                                first_chunk = False
                                if _looks_like_html(chunk):
                                    raise DownloadError(
                                        f"{url} returned an HTML page, "
                                        "not an XML snapshot"
                                    )
                            sink.write(chunk)
                            byte_count += len(chunk)
                            hasher.update(chunk)
                            if byte_count > config.max_bytes:
                                raise DownloadError(
                                    f"{url} exceeded the {config.max_bytes} byte cap"
                                )
                except BaseException:
                    # Kill the partial file on any failure, including
                    # Ctrl-C. A crashed download must leave no usable file.
                    temp_path.unlink(missing_ok=True)
                    raise
                break
        else:
            raise DownloadError(
                f"more than {MAX_REDIRECT_HOPS} redirects from {requested_url}"
            )

    sha256 = hasher.hexdigest()
    snapshot = day_dir / f"{sha256}.xml"
    # replace() is atomic on the same filesystem: readers see either the
    # old file or the complete new one, never a half-written snapshot.
    temp_path.replace(snapshot)

    _write_manifest(
        snapshot.with_suffix(".json"),
        dataset_id=config.dataset_id,
        requested_url=requested_url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        byte_count=byte_count,
        sha256=sha256,
        parser_format_version=config.parser_format_version,
        retrieved_at=_iso_z(moment),
    )

    return FetchResult(
        dataset_id=config.dataset_id,
        byte_count=byte_count,
        sha256=sha256,
        snapshot_path=snapshot,
        requested_url=requested_url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        from_cache=False,
    )


def _require_allowed_https(url: str, allowed_hosts: tuple[str, ...]) -> None:
    """Refuse a URL unless it is https and its host passes the allowlist."""
    parsed = httpx.URL(url)
    if parsed.scheme != "https":
        raise DownloadError(f"{url} must use https, got {parsed.scheme!r}")
    if not _host_allowed(parsed.host, allowed_hosts):
        raise DownloadError(f"host {parsed.host!r} in {url} is not allowlisted")


def _host_allowed(host: str, allowed_hosts: tuple[str, ...]) -> bool:
    """True when host is an allowlist entry or a subdomain of one.

    Matching is on dot boundaries: evil-www.treasury.gov ends with the
    same text as www.treasury.gov but is not a subdomain of it.
    """
    host = host.lower()

    for allowed_host in allowed_hosts:
        if host == allowed_host or host.endswith("." + allowed_host):
            return True

    return False


def _looks_like_html(first_chunk: bytes) -> bool:
    """True when the body opens like an HTML page instead of XML:
    optional whitespace or a UTF-8 BOM first, then <html or
    <!doctype html in any case.
    """
    head = first_chunk.lstrip()
    if head.startswith(b"\xef\xbb\xbf"):
        head = head[3:]
    head = head[:64].lower()
    return head.startswith(b"<html") or head.startswith(b"<!doctype html")


def _load_manifest(manifest_path: Path) -> dict | None:
    """Read a manifest. A missing or broken manifest in the cache is not
    fatal: we fall back to the file's own size and skip the URL fields."""
    if not manifest_path.exists():
        return None
    try:
        with manifest_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_manifest(manifest_path: Path, **fields: object) -> None:
    """Write the provenance record for one snapshot, atomically.

    Every value must be a plain JSON type. Passing a config object here
    would crash json.dumps, so callers pass the fields they want.
    """
    temp_path = manifest_path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(fields, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temp_path.replace(manifest_path)


def _iso_z(moment: datetime) -> str:
    """UTC ISO-8601 with a Z suffix, the timestamp format the graph uses."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
