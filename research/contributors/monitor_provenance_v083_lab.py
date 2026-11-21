# REMURA Contributors v0.83 LAB — 21/11/2026 (Europe/Rome)
# Parse only ALREADY SUPPLIED text and run metadata. NO GitHub/Cloudflare calls.
"""Fail-closed offline triage of daily D1 evidence and workflow provenance.

Input is caller-supplied and NOT a direct provider or GitHub attestation.
Historical GREEN cannot substitute for missing same-day data.
No account IDs, secrets, raw logs or user information appear in output.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import re
import sys

FIELDS = frozenset({
    "REMURA_CF_ACCOUNT_QUOTA", "UTC_DAY",
    "D1_ACCOUNT_ROWS_READ_ESTIMATE", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE",
    "D1_FREE_READ_LIMIT", "D1_FREE_WRITE_LIMIT",
    "REAL_ACCOUNT_DAILY_USAGE",
})
PAIR = re.compile(r"^([A-Z][A-Z0-9_]{2,49})=([ -~]{1,180})$")
SHA = re.compile(r"^[a-f0-9]{40}$")
NUMBER = re.compile(r"^(?:0|[1-9][0-9]{0,12})$")
MAX_TEXT = 80000
MAX_AGE = timedelta(hours=6)
FUTURE_SKEW = timedelta(minutes=2)
READ_LIMIT = 5_000_000
WRITE_LIMIT = 100_000

class EvidenceProblem(ValueError):
    pass

def utc(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise EvidenceProblem("bad_timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceProblem("bad_timestamp") from exc
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise EvidenceProblem("timezone_not_utc")
    return result.astimezone(timezone.utc)

def provenance(run: object, now: datetime) -> str:
    if not isinstance(run, dict) or set(run) != {
        "source", "run_id", "branch", "workflow", "conclusion", "started_utc", "head_sha"
    }:
        raise EvidenceProblem("run_metadata_invalid")
    if (run["source"] != "SUPPLIED_GITHUB_ACTIONS_METADATA"
            or type(run["run_id"]) is not int or not 0 < run["run_id"] < 10**16
            or run["branch"] != "main"
            or run["workflow"] != "REMURA Cloudflare Free Budget DAILY (read-only)"
            or not isinstance(run["head_sha"], str) or not SHA.fullmatch(run["head_sha"])
            or run["conclusion"] not in ("success", "failure", "cancelled", "timed_out")):
        raise EvidenceProblem("run_lineage_invalid")
    start = utc(run["started_utc"])
    if now - start > MAX_AGE or start > now + FUTURE_SKEW or start.date() != now.date():
        return "STALE_OR_OTHER_DAY"
    return "WORKFLOW_SUCCESS_METADATA_ONLY" if run["conclusion"] == "success" else "WORKFLOW_INCOMPLETE"

def parse_known(text: object) -> dict[str, str]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_TEXT:
        raise EvidenceProblem("log_invalid_or_oversized")
    values: dict[str,str] = {}
    for line in text.splitlines():
        # Only exact allowlisted key/value lines; arbitrary stdout is ignored,
        # never reprinted. Ambiguous duplicates fail closed.
        if len(line) > 1000:
            raise EvidenceProblem("oversized_line")
        hit = PAIR.fullmatch(line.strip())
        if not hit or hit.group(1) not in FIELDS:
            continue
        k, v = hit.groups()
        if k in values:
            raise EvidenceProblem("duplicate_known_field")
        values[k] = v
    return values

def count(values: dict[str,str], name: str, bound: int) -> int:
    raw = values.get(name)
    if not isinstance(raw, str) or not NUMBER.fullmatch(raw):
        raise EvidenceProblem("invalid_counter")
    integer = int(raw)
    if integer > bound:
        raise EvidenceProblem("counter_outside_bounds")
    return integer

def parse_d1(text: object, day: str) -> str:
    values = parse_known(text)
    if values.get("REMURA_CF_ACCOUNT_QUOTA") not in ("OK", "WARNING", "CRITICAL"):
        return "UNKNOWN_NOT_ZERO"
    source = values.get("UTC_DAY")
    if source != f"{day}; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING":
        return "DAY_OR_SOURCE_UNVERIFIED"
    try:
        reads = count(values, "D1_ACCOUNT_ROWS_READ_ESTIMATE", 10**12)
        writes = count(values, "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE", 10**12)
        if (count(values, "D1_FREE_READ_LIMIT", 10**12) != READ_LIMIT or
                count(values, "D1_FREE_WRITE_LIMIT", 10**12) != WRITE_LIMIT):
            return "REFERENCE_LIMIT_MISMATCH"
    except EvidenceProblem:
        return "COUNTERS_INVALID"
    if values["REMURA_CF_ACCOUNT_QUOTA"] != "OK" or reads >= READ_LIMIT or writes >= WRITE_LIMIT:
        return "CAUTION_OR_LIMIT"
    return "ADAPTIVE_ESTIMATE_PRESENT_NOT_BILLING"

def assess(run: object, d1_log: object, *, now_utc: datetime) -> dict[str,object]:
    result: dict[str, object] = {
        "schema": "remura.contributors.monitor_provenance.v083.lab",
        "version": "0.83", "mode": "OFFLINE_UNVERIFIED_INPUT",
        "monitor": "UNKNOWN", "d1_daily": "UNKNOWN_NOT_ZERO",
        "access_free_seats": "UNKNOWN",
        "billing_attested": False, "d1_usage_attested": False,
        "input_is_live": False, "automatic_deploy_allowed": False,
        "decision": "NO_GO",
    }
    try:
        if not isinstance(now_utc, datetime) or now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
            raise EvidenceProblem("clock_not_utc")
        stamp = now_utc.astimezone(timezone.utc)
        result["monitor"] = provenance(run, stamp)
        result["d1_daily"] = parse_d1(d1_log, stamp.date().isoformat())
        # Do not promote complete-looking synthetic input to GO, including run success.
    except (EvidenceProblem, TypeError, ValueError, UnicodeError):
        result["monitor"] = "INVALID_OR_UNVERIFIABLE"
        result["d1_daily"] = "UNKNOWN_NOT_ZERO"
    return result

def synthetic() -> tuple[dict[str,object],str,datetime]:
    t = datetime(2026,11,21,18,0,tzinfo=timezone.utc)
    meta = {
        "source":"SUPPLIED_GITHUB_ACTIONS_METADATA", "run_id":44919682812,
        "branch":"main", "workflow":"REMURA Cloudflare Free Budget DAILY (read-only)",
        "conclusion":"failure", "started_utc":"2026-11-21T15:32:05Z",
        "head_sha":"a"*40
    }
    log = "REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA\nREAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED"
    return meta,log,t

def main(argv:list[str])->int:
    if argv!=["--synthetic-self-check"]:
        print("REMURA_V083_PROVENANCE=NO_GO_BAD_ARGUMENTS")
        return 2
    meta,log,t=synthetic()
    summary=assess(meta,log,now_utc=t)
    if summary["d1_daily"]!="UNKNOWN_NOT_ZERO" or summary["monitor"]!="WORKFLOW_INCOMPLETE":
        print("REMURA_V083_PROVENANCE=NO_GO_FIXTURE_INVALID")
        return 3
    print(json.dumps(summary,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
