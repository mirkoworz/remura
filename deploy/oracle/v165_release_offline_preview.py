#!/usr/bin/env python3
"""REMURA v1.65 offline release *preview* only.

No command in this module can install, merge, deploy, restart, back up, or
inspect the VPS. It validates pinned Git blobs from the isolated DRAFT branch,
and models a nine-page version/cache transition entirely in memory.

IMPORTANT: a simulated timestamp and matching source SHA NEVER attest an
actual installation, a consistent SQLite backup, billing, or LIVE readiness.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
from zoneinfo import ZoneInfo

SCHEMA = "remura-v165-offline-release-preview-v1"
BASE_MAIN_SHA = "5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74"
BASE_LIVE_VERSION = "v1.64"
FUTURE_VERSION = "v1.65"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
PAGE_NAMES = (
    "index.html", "asset.html", "mercati.html", "forex.html",
    "catalogo.html", "statistica-squali.html", "stato-prezzi.html",
    "fonti.html", "impostazioni.html",
)
BACKEND = (
    "scripts/private_server.py",
    "scripts/storage_inventory_v165.py",
    "scripts/storage_cache_v165.py",
)
SOURCE_BLOBS = {
    "index.html": "b41ebbf9f768bfa4a57d625620eb9b3f53b3e445",
    "asset.html": "2036c63dc8ff2930636f6dc9d4259fa2353c8b11",
    "mercati.html": "10d20744ed69531d4d51bdda194c01b5fcd116f3",
    "forex.html": "e4f7c9fea8924dd3a1fffed18363e30dd539f8ca",
    "catalogo.html": "2847a1ecb36ee92aa36e14444db5770f846f4978",
    "statistica-squali.html": "4cd8ca9420f95deaa916fa5853d9fae697f0ad0a",
    "stato-prezzi.html": "193211906f303db1b8ef9e6c1af4e30e01b6ce4c",
    "fonti.html": "17b6ebedf83531e070f150d29ad508c1812c0cee",
    "impostazioni.html": "d772e2e8313148384fc2495faf189f8b1fa9d800",
    "nav.js": "d35c9d06f9c64a10938f30ec7e7ae7b2f2c5fbec",
    "sw.js": "6e447938533ff91183959d1902853634e6a83257",
    "scripts/private_server.py": "ce4a70d1c8eb91cc0245f3846bb612c7b701d5ae",
    "scripts/storage_inventory_v165.py": "2b6de7167ba88f0140df1339f85a1918dc14d307",
    "scripts/storage_cache_v165.py": "54d0a2e9a0ee464d11e780bd807d6efcd721aa4f",
}
SOURCE_NAV_TAG = b"nav.js?v=164"
TARGET_NAV_TAG = b"nav.js?v=165"
SOURCE_BANNER = "REMURA · Aggiornamento v1.64 · 05/11/2026 18:03 (Italia, preparazione)".encode()
TARGET_BANNER_PREFIX = "REMURA · Aggiornamento v1.65 · "
SOURCE_SW = b'remura-shell-v78-v1.64-shark-cinematic'
TARGET_SW = b'remura-shell-v79-v1.65-storage-diagnostic'
MAX_READ_BYTES = 3_000_000
REQUIRED_LIVE_GATES = (
    "explicit_separate_release_authorization",
    "private_ingress_and_tailscale_acl_verified",
    "live_sha_and_exact_file_manifest_attested",
    "oracle_billing_and_all_free_quotas_checked",
    "sqlite_consistent_backup_completed",
    "isolated_sqlite_restore_integrity_verified",
    "v164_code_rollback_tested",
    "pinned_release_and_autoupdater_reconciliation",
    "collector_continuity_and_no_extra_calls_verified",
    "nine_page_real_rome_time_banner_verified",
)


def require(condition, reason):
    if not condition:
        raise ValueError("STOP_" + reason)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii")
                         + b"\0" + data).hexdigest()


def read_sources(root: Path) -> dict[str, bytes]:
    """Read only a finite fixed allowlist; no traversal of private storage."""
    require(isinstance(root, Path) and root.is_dir() and not root.is_symlink(),
            "INVALID_LOCAL_CHECKOUT")
    out = {}
    for name in SOURCE_BLOBS:
        path = root / name
        require(not path.parent.is_symlink(), "UNEXPECTED_SOURCE_DIRECTORY_LINK")
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_READ_BYTES,
                "NOT_A_REGULAR_BOUNDED_SOURCE_FILE")
        data = path.read_bytes()
        require(len(data) <= MAX_READ_BYTES, "SOURCE_TOO_LARGE")
        out[name] = data
    return out


def _banner(stamp: str | None) -> bytes:
    if stamp is None:
        return (TARGET_BANNER_PREFIX + "DATA_ORA_REALE_SOLO_AL_RILASCIO").encode()
    require(re.fullmatch(r"\d{2}/\d{2}/20\d{2} \d{2}:\d{2} \(Italia\)", stamp)
            is not None, "INSTALL_STAMP_INVALID")
    return (TARGET_BANNER_PREFIX + stamp).encode()


def preview(sources: dict[str, bytes], *, base_main_sha=BASE_MAIN_SHA,
            simulated_install_time: datetime | None = None) -> dict[str, bytes]:
    """Compute the future candidate ONLY in memory; no installer exists."""
    require(base_main_sha == BASE_MAIN_SHA, "UNPINNED_MAIN_BASE")
    require(type(sources) is dict and set(sources) == set(SOURCE_BLOBS),
            "UNREVIEWED_SOURCE_FILE_SET")
    for name, expected in SOURCE_BLOBS.items():
        body = sources[name]
        require(type(body) is bytes and len(body) <= MAX_READ_BYTES
                and git_blob(body) == expected, "SOURCE_BLOB_DIVERGED")

    if simulated_install_time is None:
        stamp = None
    else:
        require(isinstance(simulated_install_time, datetime)
                and simulated_install_time.tzinfo is not None
                and simulated_install_time.utcoffset() is not None,
                "SIMULATED_TIME_MUST_BE_AWARE")
        # Test-only deterministic timestamp; not proof that installation happened.
        stamp = simulated_install_time.astimezone(
            ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M (Italia)")

    staged = dict(sources)
    for page in PAGE_NAMES:
        data = staged[page]
        require(data.count(SOURCE_NAV_TAG) == 1
                and TARGET_NAV_TAG not in data, "NINE_PAGE_CACHE_REFERENCE")
        staged[page] = data.replace(SOURCE_NAV_TAG, TARGET_NAV_TAG)

    nav = staged["nav.js"]
    require(nav.count(SOURCE_BANNER) == 1
            and b"release.id=\"rm-release\"" in nav
            and b"document.body.prepend(release)" in nav,
            "GLOBAL_TOP_BANNER_MISSING")
    staged["nav.js"] = nav.replace(SOURCE_BANNER, _banner(stamp))
    sw = staged["sw.js"]
    require(sw.count(SOURCE_SW) == 1 and TARGET_SW not in sw
            and b'url.pathname.includes("/private-api/")' in sw,
            "OFFLINE_SW_SAFETY")
    staged["sw.js"] = sw.replace(SOURCE_SW, TARGET_SW)
    require(all(x.count(TARGET_NAV_TAG) == 1 for name,x in staged.items()
                if name in PAGE_NAMES), "NINE_PAGE_VERSION_MISMATCH")
    require(b"REMURA_STORAGE_DIAG_ENABLED" in staged["scripts/private_server.py"]
            and b"_STORAGE_CACHE.peek()" in staged["scripts/private_server.py"],
            "BACKEND_DEFAULT_OFF_MISSING")
    require(b"NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
            in staged["scripts/storage_inventory_v165.py"]
            and b"NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
            in staged["scripts/storage_cache_v165.py"], "RESEARCH_GUARD_MISSING")
    return staged


def legacy_release_structure(root: Path) -> dict[str, bool]:
    """AST inspection only: does NOT run the 1.64 installer/reconciler."""
    definitions = {
        "deploy/oracle/release_v164.py": {
            "preflight", "verify_target", "saved_rollback",
            "restore_originals", "release_stamp", "apply", "rollback_from"},
        "deploy/oracle/reconcile_v164.py": {
            "inspect", "validate_target", "backups_present", "commit_state"},
        "deploy/oracle/backup_v156.py": set(),
    }
    result = {}
    for name, required in definitions.items():
        path = root / name
        require(path.is_file() and not path.is_symlink(), "LEGACY_PROOF_SOURCE_MISSING")
        data = path.read_bytes()
        require(len(data) <= 1_000_000, "LEGACY_PROOF_SOURCE_OVERSIZED")
        tree = ast.parse(data, filename=name)
        found = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        require(required.issubset(found), "LEGACY_RELEASE_STRUCTURE_MISSING")
        result[name] = True
    return result


def status(root: Path):
    staged = preview(read_sources(root))
    structure = legacy_release_structure(root)
    # Explicit NO-GO: source consistency is not independent LIVE evidence.
    return {
        "schema": SCHEMA,
        "state": "OFFLINE_PREVIEW_ONLY_NO_RELEASE",
        "baseMainSha": BASE_MAIN_SHA,
        "sourceFilesChecked": len(SOURCE_BLOBS),
        "versionedPagesPreviewed": len(PAGE_NAMES),
        "legacyGuardModulesInspected": len(structure),
        "previewSha256": hashlib.sha256(
            b"".join(name.encode() + b"\0" + staged[name]
                     for name in sorted(staged))).hexdigest(),
        "previewWrittenToDisk": False,
        "liveVpsContacted": False,
        "sqliteOpened": False,
        "backupOrRestorePerformed": False,
        "rollbackPerformed": False,
        "autoupdaterChanged": False,
        "releaseInstalled": False,
        "pendingLiveGates": list(REQUIRED_LIVE_GATES),
        "operationalDecision": NO_GO,
    }


def main():
    p = argparse.ArgumentParser(description="REMURA v1.65 offline draft only")
    p.add_argument("--check-offline", action="store_true", required=True)
    args = p.parse_args()
    _ = args
    print(json.dumps(status(Path(__file__).resolve().parents[2]),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
