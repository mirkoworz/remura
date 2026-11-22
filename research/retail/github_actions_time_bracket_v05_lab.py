#!/usr/bin/env python3
# REMURA Retail v0.5 LAB — GitHub-run temporal brackets, 22 Nov 2026 CET.
"""Reconcile 3 real public-repo Myfxbook commits and 6 previously observed
GitHub Actions run-metadata records. OFFLINE, no web/API/Secrets.

This proves only that immutable Git objects contain source-stamped snapshots
and that cached, server-reported Actions clocks ORDER around those stamps.
Actions created_at values are independent PLATFORM metadata, but the cached
fixture is neither a signed GitHub response nor original provider first-seen.
A later Pages run START is not proof of successful Pages deployment at that
moment; nor proof any trader had observed the information then.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha1, sha256
from pathlib import Path
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="remura.retail.github_actions_temporal_bracket.v05.lab"
SOURCE="Myfxbook Community Outlook"
HEX40=re.compile(r"^[a-f0-9]{40}$")
STAMP=re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
EVIDENCE=(
    {
        "collector_run_id":44726515105,
        "collector_run_head":"1b450ef4f4efa0940851b0d1a866375648b5e789",
        "collector_created_utc":"2026-11-20T11:18:27Z",
        "collector_completed_reported_utc":"2026-11-20T11:18:36Z",
        "commit":"32188ca6304b86190d993159260f3baf4a801e89",
        "latest_blob":"05351844eed9e2575e8651fe4a701d50b518dfbf",
        "sample_utc":"2026-11-20T11:18:32Z",
        "pages_run_id":44726531678,
        "pages_created_utc":"2026-11-20T11:18:34Z",
    },
    {
        "collector_run_id":44972218268,
        "collector_run_head":"06ebde2ce740f92fd8b44d5eb3c9d6faa57c7a07",
        "collector_created_utc":"2026-11-22T01:36:08Z",
        "collector_completed_reported_utc":"2026-11-22T01:36:21Z",
        "commit":"7c70bb9fd0e774d45c493217382c430b448af0e2",
        "latest_blob":"c2c4dfc6546fa26e315400995132fc60170cede1",
        "sample_utc":"2026-11-22T01:36:15Z",
        "pages_run_id":44972231080,
        "pages_created_utc":"2026-11-22T01:36:18Z",
    },
    {
        "collector_run_id":45004678062,
        "collector_run_head":"7c70bb9fd0e774d45c493217382c430b448af0e2",
        "collector_created_utc":"2026-11-22T08:50:31Z",
        "collector_completed_reported_utc":"2026-11-22T08:50:49Z",
        "commit":"bd19918f457809f0568aee5c674b1b36a254971e",
        "latest_blob":"eff0d57f7497f0eee9843e24a3f7694074403a18",
        "sample_utc":"2026-11-22T08:50:44Z",
        "pages_run_id":45004698324,
        "pages_created_utc":"2026-11-22T08:50:46Z",
    }
)
KEYS=frozenset(EVIDENCE[0])
class BracketError(ValueError):
    pass

def parse_utc(value):
    if type(value) is not str or not STAMP.fullmatch(value):
        raise BracketError("timestamp_noncanonical_utc")
    try:
        d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise BracketError("timestamp_noncanonical_utc") from exc
    if d.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise BracketError("timestamp_noncanonical_utc")
    return d

def git(*args):
    try:
        proc=subprocess.run(["git",*args],cwd=ROOT,capture_output=True,
                            timeout=10,check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise BracketError("offline_git_object_unavailable") from exc
    if len(proc.stdout)>500_000:
        raise BracketError("oversized_git_object")
    return proc.stdout

def digest_git_blob(payload):
    return sha1(b"blob "+str(len(payload)).encode("ascii")+b"\0"+payload).hexdigest()

def unique_keys(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            raise BracketError("duplicate_json_key")
        result[k]=v
    return result

def inspect_one(evidence):
    """No caller-supplied evidence is promoted to external attestation."""
    if type(evidence) is not dict or set(evidence)!=KEYS:
        raise BracketError("evidence_schema_invalid")
    for label in ("commit","collector_run_head","latest_blob"):
        if type(evidence[label]) is not str or not HEX40.fullmatch(evidence[label]):
            raise BracketError("invalid_git_hash")
    for label in ("collector_run_id","pages_run_id"):
        if type(evidence[label]) is not int or evidence[label]<1:
            raise BracketError("invalid_action_run_id")
    t0=parse_utc(evidence["collector_created_utc"])
    stamp=parse_utc(evidence["sample_utc"])
    t1=parse_utc(evidence["pages_created_utc"])
    completed=parse_utc(evidence["collector_completed_reported_utc"])
    if not t0<=stamp<=t1:
        raise BracketError("snapshot_outside_platform_clock_bracket")
    if completed<stamp:
        raise BracketError("collector_completion_before_snapshot")
    if (t1-t0).total_seconds()>600:
        raise BracketError("bracket_too_wide_for_fine_timing_claim")
    if git("cat-file","-t",evidence["commit"]).strip()!=b"commit":
        raise BracketError("commit_object_type_invalid")
    parent=git("rev-parse",evidence["commit"]+"^").strip().decode("ascii")
    if parent!=evidence["collector_run_head"]:
        raise BracketError("source_run_head_not_parent_commit")
    payload=git("show",evidence["commit"]+":data/myfxbook/latest.json")
    if digest_git_blob(payload)!=evidence["latest_blob"]:
        raise BracketError("committed_content_hash_mismatch")
    try:
        obj=json.loads(payload.decode("utf-8"),object_pairs_hook=unique_keys)
    except (ValueError,UnicodeError) as exc:
        raise BracketError("invalid_snapshot_json") from exc
    if (type(obj) is not dict or set(obj)!={"status","source","updatedAt","symbols"}
        or obj["status"]!="ok" or obj["source"]!=SOURCE or
        obj["updatedAt"]!=evidence["sample_utc"] or
        type(obj["symbols"]) is not dict or
        type(obj["symbols"].get("EURUSD")) is not dict or
        obj["symbols"]["EURUSD"].get("t")!=evidence["sample_utc"]):
        raise BracketError("snapshot_identity_or_clock_mismatch")
    # This is a reported server-event interval, never a clock/notary proof.
    return {
        "commit":evidence["commit"],
        "latest_git_blob":evidence["latest_blob"],
        "collector_run_id":evidence["collector_run_id"],
        "pages_run_id":evidence["pages_run_id"],
        "collector_run_created_reported_utc":evidence["collector_created_utc"],
        "sample_local_clock_utc":evidence["sample_utc"],
        "pages_run_created_reported_utc":evidence["pages_created_utc"],
        "bracket_seconds":int((t1-t0).total_seconds()),
        "collector_to_sample_seconds":int((stamp-t0).total_seconds()),
        "sample_to_pages_seconds":int((t1-stamp).total_seconds()),
        "pages_started_before_collector_run_completed":t1<completed,
        "pages_started_means_page_publicly_available":False,
        "original_provider_publication_attested":False,
        "github_server_response_signed_in_fixture":False,
        "market_data_first_seen_independently_attested":False,
        "decision_admission_allowed":False,
    }

def audit():
    rows=[inspect_one(x) for x in EVIDENCE]
    if len({r["commit"] for r in rows})!=len(rows):
        raise BracketError("duplicate_content_commit")
    if len({r["collector_run_id"] for r in rows})!=len(rows):
        raise BracketError("duplicate_source_run")
    if len({r["pages_run_id"] for r in rows})!=len(rows):
        raise BracketError("duplicate_pages_run")
    return {
        "schema":SCHEMA,
        "status":"THREE_REAL_GIT_COMMITS_WITH_CACHED_GH_RUN_INTERVALS",
        "count":len(rows),"brackets":rows,
        "evidence_limit":"GITHUB_SERVER_REPORTED_TIMES_CACHED_NOT_NOTARIZED",
        "upstream_myfxbook_publication_time_proven":False,
        "tradingview_or_cot_confirmation":False,
        "scientific_holdout_admission":False,
        "external_calls":0,"files_modified":0,"new_runs_launched":0,
    }
