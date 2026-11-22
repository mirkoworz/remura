#!/usr/bin/env python3
# REMURA Retail — independent-platform event association v0.4 LAB (22 Nov 2026)
"""Reconcile TWO already-existing GitHub Pages run metadata snapshots with
the referenced real Myfxbook commit objects, offline and strictly read-only.

The server-reported run creation clock is independent of the local Myfxbook
collector clock, but not a cryptographically notarized time proof. Metadata
here is PINNED FROM AN EARLIER CONNECTOR READ, not re-authenticated by code.
Pages success does not prove Myfxbook publication, decision availability, or
even that a particular consumer saw the page. No new runs are triggered.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path
import subprocess

from myfxbook_pinned_real_replay_v02_lab import ROOT, ReplayError, utc, unique

REPO=Path(__file__).resolve().parents[2]
SOURCE="Myfxbook Community Outlook"
PROVENANCE_SCHEMA="remura.retail.github_pages_server_event.v04.lab"
# GitHub REST Actions endpoints observed read-only on 22 Nov 2026.
# Not provider publication times. These are historical, public repository
# run metadata; future records must be independently obtained and checked.
FIXED=(
    {"commit":"32188ca6304b86190d993159260f3baf4a801e89",
     "blob":"05351844eed9e2575e8651fe4a701d50b518dfbf",
     "sample":"2026-11-20T11:18:32Z","run_id":44726531678,
     "run_created":"2026-11-20T11:18:34Z",
     "run_name":"pages build and deployment",
     "run_event":"dynamic","run_head":"32188ca6304b86190d993159260f3baf4a801e89",
     "run_conclusion":"success"},
    {"commit":"7c70bb9fd0e774d45c493217382c430b448af0e2",
     "blob":"c2c4dfc6546fa26e315400995132fc60170cede1",
     "sample":"2026-11-22T01:36:15Z","run_id":44972231080,
     "run_created":"2026-11-22T01:36:18Z",
     "run_name":"pages build and deployment",
     "run_event":"dynamic","run_head":"7c70bb9fd0e774d45c493217382c430b448af0e2",
     "run_conclusion":"success"},
)


def _git(*args):
    try:
        result=subprocess.run(["git",*args],cwd=REPO,capture_output=True,
                              check=True,timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ReplayError("git_commit_object_not_available") from exc
    if len(result.stdout)>500_000:
        raise ReplayError("git_output_oversized")
    return result.stdout


def blob_oid(data):
    return sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def review_association(*, commit, blob, sample, run_id, run_created, run_name,
                       run_event, run_head, run_conclusion):
    """Pure contract; never trust caller-supplied server metadata as attested."""
    if type(commit) is not str or len(commit)!=40 or any(c not in "0123456789abcdef" for c in commit):
        raise ReplayError("invalid_git_identity")
    if type(blob) is not str or len(blob)!=40 or any(c not in "0123456789abcdef" for c in blob):
        raise ReplayError("invalid_git_blob")
    observed=utc(sample)
    created=utc(run_created)
    if type(run_id) is not int or run_id<1:
        raise ReplayError("invalid_run_identity")
    if run_head!=commit or run_name!="pages build and deployment" or run_event!="dynamic":
        return {"status":"UNRELATED_GITHUB_EVENT_CLAIM","delta_seconds":None,
                "can_be_used_for_holdout":False}
    if run_conclusion!="success":
        return {"status":"UNFINISHED_OR_FAILED_GITHUB_EVENT","delta_seconds":None,
                "can_be_used_for_holdout":False}
    delta=int((created-observed).total_seconds())
    if delta<0 or delta>3600:
        return {"status":"CLOCK_ORDER_NOT_CREDIBLE","delta_seconds":delta,
                "can_be_used_for_holdout":False}
    return {"status":"EXTERNAL_PLATFORM_RUN_ASSOCIATION_UNATTESTED_OFFLINE",
            "delta_seconds":delta, "can_be_used_for_holdout":False}


def audit():
    rows=[]
    for pinned in FIXED:
        data=_git("show",pinned["commit"]+":data/myfxbook/latest.json")
        if blob_oid(data)!=pinned["blob"]:
            raise ReplayError("git_blob_not_pinned")
        try:
            obj=json.loads(data.decode("utf-8"),object_pairs_hook=unique)
        except (ValueError,UnicodeError) as exc:
            raise ReplayError("unreadable_snapshot") from exc
        if (type(obj) is not dict or obj.get("updatedAt")!=pinned["sample"] or
            obj.get("source")!=SOURCE or obj.get("status")!="ok" or
            not isinstance(obj.get("symbols"),dict) or
            obj["symbols"].get("EURUSD",{}).get("t")!=pinned["sample"]):
            raise ReplayError("snapshot_not_reconciled")
        review=review_association(**pinned)
        if review["status"]!="EXTERNAL_PLATFORM_RUN_ASSOCIATION_UNATTESTED_OFFLINE":
            raise ReplayError("historical_run_claim_not_consistent")
        rows.append({
            "commit":pinned["commit"],"snapshot_utc":pinned["sample"],
            "git_blob":pinned["blob"],"github_pages_run_id":pinned["run_id"],
            "github_server_run_created_at_reported":pinned["run_created"],
            "clock_gap_seconds":review["delta_seconds"],
        })
    return {
        "schema":PROVENANCE_SCHEMA,
        "status":"TWO_GITHUB_RUN_ASSOCIATIONS_RECONCILED_OFFLINE",
        "snapshots":rows,
        "git_platform_metadata_from_connector_read":True,
        "github_api_live_called_by_module":False,
        "github_run_payload_cryptographically_signed":False,
        "github_server_receive_time_notarized":False,
        "myfxbook_provider_publication_time_proven":False,
        "independent_market_first_seen_proven":False,
        "decision_time_access_proven":False,
        "institutional_edge_proven":False,
        "holdout_science_admission":False,
        "server_run_is_not_market_price_timestamp":True,
        "new_workflows_launched":0,
        "secrets_used":False,
    }
