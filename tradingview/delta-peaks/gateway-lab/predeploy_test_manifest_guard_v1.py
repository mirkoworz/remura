#!/usr/bin/env python3
# REMURA Test Worker Manifest Guard v0.8.18 — 13/11/2026, ore 13:58 CET
# Pure offline safety validation. No Wrangler, API requests, secrets or deploy.
"""Validate isolated webhook TEST manifest; unresolved examples MUST NOT deploy."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

EXPECTED_NAME = "remura-tv-webhook-test"
EXPECTED_DB = "remura-tv-lab-test"
DB_ID_RE = re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$", re.I)
NS_ID_RE = re.compile(r"^[1-9][0-9]{0,14}$")
ROOT_FIELDS = {"$comment", "name", "main", "compatibility_date",
               "workers_dev", "vars", "d1_databases", "ratelimits"}


class ManifestError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ManifestError(code)


def verify_manifest(cfg: object) -> str:
    require(type(cfg) is dict and set(cfg) == ROOT_FIELDS, "manifest_keys")
    require(cfg["name"] == EXPECTED_NAME, "test_worker_name_mismatch")
    require(cfg["main"] == "worker.mjs", "main_code_unknown")
    require(cfg["workers_dev"] is True, "workers_dev_route_expected")
    require(type(cfg["compatibility_date"]) is str
            and cfg["compatibility_date"] == "2026-11-13", "compat_date_invalid")
    require(type(cfg["$comment"]) is str and "SOLO ESEMPIO" in cfg["$comment"],
            "must_be_clearly_marked_example")
    require(cfg["vars"] == {"INGEST_ENABLED": "false"}, "ingest_not_proven_off")
    db = cfg["d1_databases"]
    require(type(db) is list and len(db) == 1 and type(db[0]) is dict
            and set(db[0]) == {"binding", "database_name", "database_id"}
            and db[0]["binding"] == "TELEMETRY_DB"
            and db[0]["database_name"] == EXPECTED_DB, "d1_not_isolated_test")
    db_id = db[0]["database_id"]
    require(type(db_id) is str, "d1_id_invalid")
    limits = cfg["ratelimits"]
    require(type(limits) is list and len(limits) == 1
            and type(limits[0]) is dict
            and set(limits[0]) == {"name", "namespace_id", "simple"}
            and limits[0]["name"] == "INGEST_RATE_LIMITER", "limiter_missing")
    rl = limits[0]
    require(rl["simple"] == {"limit": 20, "period": 60},
            "limiter_configuration_wrong")
    ns = rl["namespace_id"]
    require(type(ns) is str, "limiter_namespace_invalid")
    # The committed template MUST remain undeployable; only in-memory synthetic
    # tests may substitute a UUID and namespace to prove ready structure.
    if (db_id == "REPLACE_WITH_D1_TEST_UUID"
            and ns == "REPLACE_WITH_UNIQUE_POSITIVE_INTEGER"):
        return "EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS"
    require(DB_ID_RE.fullmatch(db_id) is not None, "d1_uuid_not_real")
    require(NS_ID_RE.fullmatch(ns) is not None, "namespace_not_integer_string")
    return "STRUCTURALLY_READY_OFFLINE_ONLY"


def main() -> int:
    example = Path(__file__).with_name("wrangler.webhook-test.EXAMPLE.json")
    try:
        status = verify_manifest(json.loads(example.read_text(encoding="utf-8")))
    except (ManifestError, ValueError, OSError):
        print("REMURA_TEST_DEPLOY_MANIFEST=INVALID")
        return 2
    print("REMURA_TEST_DEPLOY_MANIFEST=" + status)
    print("WORKER_SEPARATE=remura-tv-webhook-test; DB=TEST_ONLY; INGEST=OFF")
    print("DEPLOY=NOT_AUTHORIZED; BILLING=UNVERIFIED; SECRETS=NOT_PRESENT")
    return 0 if status == "EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS" else 2


if __name__ == "__main__":
    sys.exit(main())
