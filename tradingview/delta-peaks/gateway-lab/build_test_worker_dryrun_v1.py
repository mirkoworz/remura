#!/usr/bin/env python3
# REMURA v0.8.23 — 13/11/2026, 15:27:38 Europe/Rome
# 100% LOCAL: fake UUID + namespace only, NO deploy, NO Cloudflare credentials.
"""Build a synthetic, temporary Wrangler config for official --dry-run.

The real D1 UUID, any secrets, and the Production Worker are deliberately
unreachable. Never use generated files for a live deploy or credentialed run.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from predeploy_test_manifest_guard_v1 import verify_manifest, ManifestError

BASE = Path(__file__).resolve().parent
EXAMPLE = BASE / "wrangler.webhook-test.EXAMPLE.json"
CODE = BASE / "worker.mjs"
FAKE_TEST_UUID = "00000000-0000-4000-8000-000000000002"
FAKE_LIMITER_NAMESPACE = "987654321"
EXPECTED_WORKER = "remura-tv-webhook-test"


class DryRunError(ValueError):
    pass


def make_bundle(outdir: Path, *, example_path: Path = EXAMPLE,
                code_path: Path = CODE) -> Path:
    outdir = Path(outdir)
    if outdir.exists():
        raise DryRunError("destination_must_not_exist")
    template = json.loads(Path(example_path).read_text(encoding="utf-8"))
    try:
        source_status = verify_manifest(template)
    except ManifestError:
        raise DryRunError("source_template_invalid") from None
    if source_status != "EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS":
        raise DryRunError("source_template_must_remain_blocked")
    materialized = dict(template)
    materialized.pop("$comment")
    materialized["d1_databases"] = [dict(template["d1_databases"][0])]
    materialized["ratelimits"] = [
        dict(template["ratelimits"][0], simple=dict(template["ratelimits"][0]["simple"]))
    ]
    materialized["d1_databases"][0]["database_id"] = FAKE_TEST_UUID
    materialized["ratelimits"][0]["namespace_id"] = FAKE_LIMITER_NAMESPACE
    guarded = dict(materialized, **{"$comment": template["$comment"]})
    try:
        generated_status = verify_manifest(guarded)
    except ManifestError:
        raise DryRunError("generated_synthetic_manifest_invalid") from None
    if generated_status != "STRUCTURALLY_READY_OFFLINE_ONLY":
        raise DryRunError("generated_synthetic_manifest_invalid")
    if materialized["name"] != EXPECTED_WORKER or materialized["vars"] != {
        "INGEST_ENABLED": "false"
    }:
        raise DryRunError("runtime_not_proven_disabled")
    code = Path(code_path).read_text(encoding="utf-8")
    if "INGEST_RATE_LIMITER" not in code or "INGEST_ENABLED" not in code:
        raise DryRunError("fail_closed_worker_source_unknown")
    outdir.mkdir(parents=True, exist_ok=False)
    (outdir / "wrangler.json").write_text(
        json.dumps(materialized, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copyfile(code_path, outdir / "worker.mjs")
    return outdir / "wrangler.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OFFLINE synthetic Wrangler build")
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = make_bundle(args.outdir)
    except (DryRunError, OSError, TypeError, ValueError, KeyError):
        print("REMURA_WRANGLER_DRYRUN_PREP=BLOCKED")
        return 2
    print("REMURA_WRANGLER_DRYRUN_PREP=SYNTHETIC_ONLY")
    print("NAME=remura-tv-webhook-test; TARGET=FAKE_D1_TEST_UUID; INGEST=OFF")
    print("LIMITER=FAKE_NAMESPACE; SECRETS=NONE; CLOUDFLARE_API=NOT_CALLED")
    print("DEPLOY=FORBIDDEN; READY_FOR_REAL_DEPLOY=NO")
    # Only path of a temporary configuration, not its contents or identifiers.
    print("WRANGLER_CONFIG_PATH=" + str(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
