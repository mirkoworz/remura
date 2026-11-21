# REMURA Contributors v0.79 LAB — 21/11/2026 17:15 CET.
# Exact Git SHA-1 blob source lock. OFFLINE; never build/deploy/activate Cloudflare.
"""Verify v0.78 Worker candidate and security contracts byte-for-byte before review.

The lock certifies only repository bytes, NOT the runtime behavior of Cloudflare.
A source match does not authorize deployment or modify any file.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path, PurePosixPath
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCKED_BLOBS = {
    "research/contributors/private_levels_composition_v078_lab.mjs": "318d3948ab0b2550daf738cc7d0ebcd223f6c7d4",
    "research/contributors/private_worker_router_v078_lab.mjs": "c25a794f53fda5efa66366b951bf046892f8d8b0",
    "research/contributors/private_assets_v078_lab.mjs": "fe66078ffff78c3edaf12908caa564d63cbe7fcc",
    "research/contributors/owner_level_integrity_v078_lab.mjs": "c947b968d5fd1693422162410bd8ff97660c56ad",
    "research/contributors/owner_level_audit_http_v078_lab.mjs": "ec0818ba566a47b0382c6e5adeb81f0ce9c419fb",
    "research/contributors/owner_level_audit_v077_lab.mjs": "242740657e89b561a26c08a1758e80f25777166e",
    "research/contributors/level_attempt_journal_v076_lab.mjs": "ea905642f82c752e47ef6b714c2e4a63324e651b",
    "research/contributors/level_intent_precheck_v076_lab.mjs": "d242d74b6a1049c27663cff7075e50ab19a1a63d",
    "research/contributors/new_level_attempts_v076_lab.sql": "bad46538dc6c21cbee6a4311af393071569a296f",
    "research/contributors/new_level_owner_audit_v077_lab.sql": "68687452340012ea8a754f8dbdb66e2c78ac9aba",
    "research/contributors/durable_level_api_v076_lab.mjs": "110f9d181468bc61c9fdff6d3c08caddc2d66bc0",
    "research/contributors/access_binding_candidate.mjs": "3bb233eba371728b2d5ef146826efe0a4045dee9",
    "research/contributors/d1_access_candidate.mjs": "e5dd70b5a0243130a1a95bee4ea4cb6266b08b68",
    "research/contributors/http_access_candidate.mjs": "eeca1d27f202f10473116504fc9bf8d65934805d",
}
HEX40 = re.compile(r"^[a-f0-9]{40}$")

class SourceLockError(ValueError):
    pass


def checked_path(name: str) -> PurePosixPath:
    if not isinstance(name, str):
        raise SourceLockError("bad_path_type")
    p = PurePosixPath(name)
    if (p.is_absolute() or name != p.as_posix() or len(p.parts) != 3
            or p.parts[:2] != ("research", "contributors")
            or p.suffix not in (".mjs", ".sql")
            or name.find("\\") >= 0 or ".." in name.split("/")):
        raise SourceLockError("unsafe_source_path")
    return p


def git_blob_sha(content: bytes) -> str:
    if not isinstance(content, bytes):
        raise SourceLockError("non_byte_content")
    return sha1(b"blob " + str(len(content)).encode("ascii") + b"\\0" + content).hexdigest()


def verify_blob(name: str, expected: str, *, root: Path = ROOT) -> bool:
    path = checked_path(name)
    if not isinstance(expected, str) or not HEX40.fullmatch(expected):
        raise SourceLockError("invalid_sha")
    if not isinstance(root, Path):
        raise SourceLockError("invalid_root")
    candidate = root.joinpath(*path.parts)
    if candidate.is_symlink() or not candidate.is_file():
        raise SourceLockError("missing_or_symlink_source")
    payload = candidate.read_bytes()
    if not payload or len(payload) > 200_000:
        raise SourceLockError("source_size_invalid")
    if git_blob_sha(payload) != expected:
        raise SourceLockError("source_blob_drift")
    return True


def verify_contract(*, root: Path = ROOT) -> dict[str, object]:
    if len(LOCKED_BLOBS) != 14 or len(set(LOCKED_BLOBS)) != 14:
        raise SourceLockError("manifest_incomplete")
    for name, expected in LOCKED_BLOBS.items():
        verify_blob(name, expected, root=root)
    composition = (root/"research/contributors/private_levels_composition_v078_lab.mjs").read_text(encoding="utf-8")
    router = (root/"research/contributors/private_worker_router_v078_lab.mjs").read_text(encoding="utf-8")
    if ("export default" in composition or "node:fs" in composition or
            "export default" in router or "PRIVATE_WORKER_V078" not in router or
            "OFFLINE_FIXTURE_ONLY" not in router):
        raise SourceLockError("not_a_disabled_candidate")
    return {
        "schema": "remura.contributors.staging_source_lock.v079.lab",
        "version": "0.79",
        "locked_sources": 14,
        "status": "LAB_SOURCE_LOCK_MATCH",
        "production_runtime_attested": False,
        "automatic_deploy_allowed": False,
    }


def main(argv: list[str]) -> int:
    if argv != ["--check"]:
        print("REMURA_V079_SOURCE_LOCK=NO_GO_BAD_ARGUMENTS")
        return 2
    try:
        result = verify_contract()
    except (OSError, UnicodeError, SourceLockError):
        print("REMURA_V079_SOURCE_LOCK=NO_GO_DRIFT_OR_UNVERIFIABLE")
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
