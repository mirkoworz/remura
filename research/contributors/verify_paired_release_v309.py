"""Offline preflight only. No installation, network access or state mutation."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HEX = re.compile(r"[0-9a-f]{64}")
REF = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,2}")
NAMES = {"owner": "owner.zip", "contributors": "contributors.zip"}
MAX_BYTES = 150_000_000


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = value
    return result


def bounded(path, limit):
    if not path.is_file() or path.is_symlink():
        raise ValueError("not a regular file")
    with path.open("rb") as f:
        data = f.read(limit + 1)
    if not data or len(data) > limit:
        raise ValueError("invalid file size")
    return data


def verify(directory, key, trusted_sha, accepted_sequence):
    if not HEX.fullmatch(trusted_sha) or type(accepted_sequence) is not int or accepted_sequence < 0:
        raise ValueError("invalid trust state")
    manifest = bounded(directory / "release.json", 65536)
    signature = bounded(directory / "release.sig", 64)
    public_key = bounded(key, 8192)
    if len(signature) != 64 or hashlib.sha256(public_key).hexdigest() != trusted_sha:
        raise ValueError("invalid signature or untrusted key")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, data in (("manifest", manifest), ("signature", signature), ("key", public_key)):
            (root / name).write_bytes(data)
        def openssl(*args):
            return subprocess.run(["openssl", *args], cwd=root, check=True,
                                  capture_output=True, timeout=10).stdout
        der = openssl("pkey", "-pubin", "-in", "key", "-outform", "DER")
        if len(der) != 44 or not der.startswith(bytes.fromhex("302a300506032b6570032100")):
            raise ValueError("expected Ed25519 public key")
        openssl("pkeyutl", "-verify", "-pubin", "-inkey", "key", "-rawin",
                "-in", "manifest", "-sigfile", "signature")
    m = json.loads(manifest, object_pairs_hook=unique)
    if not isinstance(m, dict) or set(m) != {"schema", "sequence", "version", "updatedAt", "artifacts"}:
        raise ValueError("invalid manifest fields")
    if m["schema"] != "remura-paired-release-v1" or type(m["sequence"]) is not int or m["sequence"] <= accepted_sequence:
        raise ValueError("invalid schema or rollback/replay")
    if not isinstance(m["version"], str) or not VERSION.fullmatch(m["version"]):
        raise ValueError("invalid version")
    dt = datetime.fromisoformat(m["updatedAt"])
    if dt.tzinfo is None or dt.utcoffset() != dt.astimezone(ZoneInfo("Europe/Rome")).utcoffset():
        raise ValueError("expected Italian offset")
    if not isinstance(m["artifacts"], dict) or set(m["artifacts"]) != set(NAMES):
        raise ValueError("both role artifacts required")
    for role, name in NAMES.items():
        a = m["artifacts"][role]
        if not isinstance(a, dict) or set(a) != {"name", "sha256", "size", "ref"} or a["name"] != name:
            raise ValueError("invalid role artifact")
        if not isinstance(a["sha256"], str) or not HEX.fullmatch(a["sha256"]) or not isinstance(a["ref"], str) or not REF.fullmatch(a["ref"]):
            raise ValueError("invalid artifact digest or ref")
        if type(a["size"]) is not int or not 0 < a["size"] <= MAX_BYTES:
            raise ValueError("invalid artifact size")
        data = bounded(directory / name, a["size"])
        if len(data) != a["size"] or hashlib.sha256(data).hexdigest() != a["sha256"]:
            raise ValueError("artifact integrity failure")
    return {"state": "VERIFIED_NOT_DEPLOYED", "sequence": m["sequence"], "version": m["version"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--trusted-key-sha256", required=True)
    parser.add_argument("--accepted-sequence", required=True, type=int)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.directory, args.public_key, args.trusted_key_sha256, args.accepted_sequence)))
    except (ValueError, TypeError, OSError, subprocess.SubprocessError):
        parser.exit(1, "REJECTED: signature, trust, release or artifact validation failed\n")


if __name__ == "__main__":
    main()
