#!/usr/bin/env python3
"""REMURA Track B: verified, ephemeral, aggregate-only SQLite census.

Opt-in, ONE SHOT. Runs as the unprivileged 'remura' OS account on the VPS;
the only remotely fetched code is pinned to the immutable Git commit below,
and each blob is verified before execution. Never modifies the database,
working tree, Python install, backend, timers, Tailscale or broker APIs.
Never outputs private URL, broker/account names, OHLC, tokens, single events,
file paths or errors that may contain secrets. Standard library only.

Only use this script on an authorized REMURA VPS. The GitHub network fetches
may incur negligible outbound traffic, but NO new external data-provider API
calls are made. Its outputs are research readiness counters, not trade signals.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import types
import urllib.request

SOURCE_COMMIT = "20145d17458b044ce3c7ce5ec0627e9e9708687c"
RAW_BASE = (
    "https://raw.githubusercontent.com/mirkoworz/remura/"
    + SOURCE_COMMIT + "/scripts/"
)
BLOBS = {
    "shark_cot_paired_baseline": "5126cb474887e2b261b8d0ae1f848eaeb59602de",
    "shark_data_readiness": "4dca257dabb699f72c7304aef8e31a87ca04d794",
    "shark_research_census": "e91351f3aee433fd983ae53030c8aab93af6b606",
}
DB_PATH = "/opt/remura/private/remura-prices.sqlite3"
MAX_SOURCE_BYTES = 30 * 1024


class _DenyRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("redirect_not_allowed")


def _fetch(name):
    """One pinned HTTPS GET per verified file; no proxies or redirects."""
    if name not in BLOBS:
        raise ValueError("unlisted_research_source")
    request = urllib.request.Request(
        RAW_BASE + name + ".py", method="GET",
        headers={"User-Agent": "REMURA-private-research-probe/1",
                 "Accept": "text/plain"},
    )
    transport = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _DenyRedirects()
    )
    with transport.open(request, timeout=12) as response:
        if response.status != 200:
            raise ValueError("source_not_found")
        raw = response.read(MAX_SOURCE_BYTES + 1)
    return raw


def _git_blob_hash(data):
    if not isinstance(data, bytes):
        raise ValueError("binary_source_required")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_verified(fetch=None):
    """Load into memory, after checking ALL three immutable Git blob hashes."""
    if sys.version_info < (3, 10):
        raise ValueError("python_runtime_unsupported")
    fetch = _fetch if fetch is None else fetch
    source = {}
    for name, expected_blob in BLOBS.items():
        raw = fetch(name)
        if (not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_SOURCE_BYTES
                or _git_blob_hash(raw) != expected_blob):
            raise ValueError("source_integrity_failed")
        source[name] = raw
    # No writing __pycache__, temporary files, DB backups or code to disk.
    sys.dont_write_bytecode = True
    namespace = types.ModuleType("scripts")
    namespace.__path__ = []
    sys.modules["scripts"] = namespace
    for name, data in source.items():
        module = types.ModuleType("scripts." + name)
        module.__package__ = "scripts"
        sys.modules[module.__name__] = module
        setattr(namespace, name, module)
        exec(compile(data, "<pinned-REMURA-research>", "exec"),
             module.__dict__)
    return namespace.shark_research_census


def run(*, fetch=None, db_path=DB_PATH, as_of=None):
    """Use existing file in strictly read-only mode, no credentials or URLs."""
    census = load_verified(fetch)
    now = datetime.now(timezone.utc) if as_of is None else as_of
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset().total_seconds() != 0):
        raise ValueError("invalid_utc_clock")
    clock = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    path = Path(db_path)
    if not path.is_file():
        raise ValueError("db_not_available")
    data = census.audit_path(path, as_of=clock)
    if (data.get("schema") != "remura-shark-research-census-v1"
            or data.get("brokerCalls") != 0
            or data.get("actualTradingEdgeEstablished") is not False):
        raise ValueError("unexpected_audit")
    return data


def main():
    try:
        result = run()
        print("REMURA_TRACK_B_CENSIMENTO=COMPLETATO")
        print(json.dumps(result, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True))
        return 0
    except Exception:
        # Suppress network URL / path / private SQLite / secret-laden errors.
        print("REMURA_TRACK_B_CENSIMENTO=NON_COMPLETATO")
        print("MOTIVO=ACCESSO_ARCHIVIO_O_VERIFICA_INTEGRITA")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
