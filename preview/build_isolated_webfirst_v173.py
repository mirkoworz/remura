#!/usr/bin/env python3
"""REMURA v1.73.1 LAB: reproducible non-deployed static preview, no credentials.

Run from repository checkout. Artifacts are NOT production-ready and must not
be published without owner approval. No network calls, no Cloudflare API.
"""
import hashlib
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "remura-v1731-webfirst-ISOLATED-NOT-PUBLISHED.zip"
PUBLIC_SUFFIXES = {".html", ".js", ".css", ".svg", ".webp", ".webmanifest", ".png"}
REQUIRED = {
    "index.html", "shark-cockpit.html", "shark-cockpit.js", "shark-cockpit-core.js",
    "shark-cockpit.css", "shark-evidence-core.js", "shark-evidence-ui.js",
    "shark-focus-core.js", "shark-focus-ui.js", "shark-movers-core.js",
    "shark-movers-ui.js", "shark-trends-core.js", "shark-trends-ui.js",
    "nav.js", "nav.css", "splash.js", "splash.css", "manifest.webmanifest",
    "icon.svg", "data/myfxbook/latest.json", "capital-cloud-config.js",
}
PREVIEW_CONFIG = b"""/* REMURA isolated preview only. No production Firebase/Google auth. */
window.REMURA_FIREBASE_CONFIG = null;
"""
MAX_SIZE = 3_000_000
MAX_TOTAL = 15_000_000


def selected_sources():
    public = {}
    for p in ROOT.iterdir():
        if p.is_file() and not p.is_symlink() and p.suffix in PUBLIC_SUFFIXES:
            if p.name == "sw.js":
                continue  # No offline cache / production SW on staging preview
            public[p.name] = p
    data_root = ROOT / "data" / "myfxbook"
    for p in data_root.rglob("*.json"):
        if p.is_file() and not p.is_symlink():
            public[p.relative_to(ROOT).as_posix()] = p
    missing = REQUIRED - set(public)
    if missing:
        raise RuntimeError("REQUIRED_PUBLIC_INPUT_MISSING:" + ",".join(sorted(missing)))
    return public


def build():
    sources = selected_sources()
    content = {}
    total = 0
    for relative, p in sorted(sources.items()):
        if ".." in Path(relative).parts or relative.startswith("/") or "\\" in relative:
            raise RuntimeError("UNSAFE_PATH")
        raw = PREVIEW_CONFIG if relative == "capital-cloud-config.js" else p.read_bytes()
        if len(raw) > MAX_SIZE:
            raise RuntimeError("OVERSIZE_FILE:" + relative)
        total += len(raw)
        if total > MAX_TOTAL:
            raise RuntimeError("OVERSIZE_BUNDLE")
        content[relative] = raw

    manifest = {
        "product": "REMURA",
        "version": "1.73.1",
        "mode": "ISOLATED_WEB_FIRST_PREVIEW_ONLY",
        "source_sha": os.environ.get("GITHUB_SHA", "LOCAL_UNVERIFIED"),
        "deployed": False,
        "firebase_production_disabled": True,
        "service_worker_excluded": True,
        "private_api_available": False,
        "offline_cockpit_supported": False,
        "files_sha256": {
            path: hashlib.sha256(payload).hexdigest()
            for path, payload in sorted(content.items())
        },
    }
    content["REMURA-PREVIEW-MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, mode="w") as archive:
        for path, payload in sorted(content.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 11, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)
    print(json.dumps({
        "bundle": str(OUT.relative_to(ROOT)),
        "file_count": len(content),
        "total_uncompressed": total,
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "mode": manifest["mode"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    build()
