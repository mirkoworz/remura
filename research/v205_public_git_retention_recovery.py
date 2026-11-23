#!/usr/bin/env python3
"""REMURA V20.5: recover real PUBLIC Myfxbook observations from pinned Git ancestry.

READ ONLY. Runs over an existing local clone containing the original Git commit
objects. No provider calls, no tokens, no market/pricing claims, no cloud writes.
A Git commit where a record appears is *not* an independent first_seen of when
Myfxbook published the information. No retroactive alpha eligibility is granted.

Rebuilds full visible revision history for each symbol, rejects conflicting
timestamp versions, and distinguishes newly restored rows from the rolling
live 126-record file. Exports PUBLIC-only data if --export is specified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any

PINNED_MAIN="a1188f8af77951b9c59b7bb1facbfa6fe2f820e7"
PREFIX="data/myfxbook/history/"
MAX_REVISIONS_PER_SYMBOL=350
MAX_SYMBOLS=40
MAX_RECORDS_PER_REVISION=500
MAX_EXPORT_ROWS=50000
SYMBOL_RE=re.compile(r"^[A-Z0-9]{3,12}$")
SHA_RE=re.compile(r"^[a-f0-9]{40}$")
UTC=dt.timezone.utc


def utc(s: str) -> dt.datetime:
    if type(s) is not str or not s.endswith("Z"):
        raise ValueError("utc_z_required")
    try:
        t=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if t.utcoffset()!=dt.timedelta(0):
        raise ValueError("non_utc_timestamp")
    return t


def git(repo: Path,*args: str) -> bytes:
    proc=subprocess.run(
        ["git","-C",str(repo),*args],capture_output=True,check=False,timeout=40)
    if proc.returncode:
        raise ValueError("git_history_incomplete_or_unavailable")
    if len(proc.stdout)>8_000_000:
        raise ValueError("git_output_oversize")
    return proc.stdout


def parse_history(contents: bytes,symbol: str) -> list[dict]:
    if type(contents) is not bytes or len(contents)>4_000_000:
        raise ValueError("invalid_snapshot_bytes")
    try:
        value=json.loads(contents.decode("utf-8"),parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))
    except (ValueError,UnicodeError) as exc:
        raise ValueError("invalid_public_history_json") from exc
    if type(value) is not dict or value.get("symbol")!=symbol or type(value.get("records")) is not list:
        raise ValueError("wrong_history_schema_or_symbol")
    records=value["records"]
    if len(records)>MAX_RECORDS_PER_REVISION:
        raise ValueError("history_revision_too_large")
    prev=None
    keys=("lPct","sPct","lLots","sLots","lPos","sPos")
    for row in records:
        if type(row) is not dict:
            raise ValueError("invalid_history_row")
        stamp=utc(row.get("t"))
        if prev is not None and stamp<=prev:
            raise ValueError("history_out_of_order_duplicate")
        prev=stamp
        for key in keys:
            v=row.get(key)
            if type(v) not in (int,float) or not math.isfinite(v) or v<0:
                raise ValueError("invalid_retained_metric")
        if row["lPct"]>100 or row["sPct"]>100:
            raise ValueError("invalid_retained_percentage")
    return records


def _commits(repo: Path,path: str) -> list[tuple[str,str]]:
    text=git(repo,"log","--format=%H%x09%cI",PINNED_MAIN,"--",path).decode("ascii").strip()
    if not text:
        raise ValueError("no_git_revisions_for_symbol")
    rows=[]
    for line in text.splitlines():
        parts=line.split("\t")
        if len(parts)!=2 or not SHA_RE.fullmatch(parts[0]) or dt.datetime.fromisoformat(parts[1]).tzinfo is None:
            raise ValueError("malformed_git_history")
        rows.append((parts[0],parts[1]))
    if len(rows)>MAX_REVISIONS_PER_SYMBOL:
        raise ValueError("revision_cap_exceeded_no_silent_truncation")
    return list(reversed(rows))


def merge_public_revisions(symbol: str, revisions: list[tuple[str,str,bytes]]) -> tuple[dict,list[dict]]:
    """Pure helper, earliest revision first. Conflicts are quarantined, not repaired."""
    if type(symbol) is not str or not SYMBOL_RE.fullmatch(symbol) or not revisions:
        raise ValueError("symbol_or_revision_required")
    records={}
    conflict=set()
    first_meta={}
    current_times=set()
    current_count=0
    prior_clock=None
    for index,(sha,when,body) in enumerate(revisions):
        if type(sha) is not str or not SHA_RE.fullmatch(sha):
            raise ValueError("bad_commit_id")
        stamp=dt.datetime.fromisoformat(when)
        if stamp.tzinfo is None:
            raise ValueError("git_commit_time_without_timezone")
        if prior_clock is not None and stamp<prior_clock:
            raise ValueError("nonmonotonic_git_committer_timestamps")
        prior_clock=stamp
        rows=parse_history(body,symbol)
        times={r["t"] for r in rows}
        if index==len(revisions)-1:
            current_times=times
            current_count=len(rows)
        for row in rows:
            t=row["t"]
            canonical=json.dumps(row,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":"))
            if t not in records:
                records[t]=canonical
                first_meta[t]={"revision_sha":sha,"revision_committer_utc":when}
            elif canonical!=records[t]:
                conflict.add(t)
    safe_times=sorted(set(records)-conflict)
    missing_from_current=[t for t in safe_times if t not in current_times]
    same_current=sum(t in current_times for t in safe_times)
    # Each record already public. Store Git revision metadata, not a fictitious provider first_seen.
    preserved=[{"row":json.loads(records[t]),
                "first_visible_in_local_git_revision":first_meta[t]} for t in safe_times]
    summary={
        "symbol":symbol,"revisions_examined":len(revisions),
        "current_rolling_rows":current_count,
        "recoverable_unconflicted_rows":len(safe_times),
        "recovered_not_in_current_rolling_window":len(missing_from_current),
        "conflicting_timestamp_rows_excluded":len(conflict),
        "rows_shared_with_current":same_current,
        "earliest_current_t":min(current_times) if current_times else None,
        "earliest_recoverable_t":safe_times[0] if safe_times else None,
        "latest_recoverable_t":safe_times[-1] if safe_times else None,
        "snapshot_recovery_status":"UNCONFLICTED_PUBLIC_GIT_UNION" if not conflict else "CONFLICTS_EXCLUDED_REVIEW",
    }
    return summary,preserved


def discover_public_paths(repo: Path) -> list[str]:
    listed=git(repo,"ls-tree","-r","--name-only",PINNED_MAIN,PREFIX).decode("utf-8")
    paths=[]
    for line in listed.splitlines():
        if not line.startswith(PREFIX) or not line.endswith(".json"):
            raise ValueError("unexpected_history_source_path")
        symbol=line[len(PREFIX):-5]
        if not SYMBOL_RE.fullmatch(symbol):
            raise ValueError("unsafe_history_filename")
        paths.append(line)
    if not 30<=len(paths)<=MAX_SYMBOLS:
        raise ValueError("unexpected_public_symbol_count")
    return sorted(paths)


def audit(repo: Path, *, export: Path | None = None) -> dict:
    actual=git(repo,"rev-parse","HEAD").decode("ascii").strip()
    if actual!=PINNED_MAIN:
        raise ValueError("source_checkout_does_not_match_pinned_main")
    paths=discover_public_paths(repo)
    summaries=[]
    archive={}
    for path in paths:
        symbol=path[len(PREFIX):-5]
        versions=_commits(repo,path)
        # Must include HEAD version; old 2026 snapshots can be truncated, never rewrite.
        last_bytes=git(repo,"show",f"{PINNED_MAIN}:{path}")
        if git(repo,"show",f"{versions[-1][0]}:{path}")!=last_bytes:
            # The last path change may predate HEAD, but its blob content must match HEAD.
            raise ValueError("last_revision_not_equal_to_pinned_head")
        revisions=[(sha,at,git(repo,"show",f"{sha}:{path}")) for sha,at in versions]
        summary,rows=merge_public_revisions(symbol,revisions)
        summaries.append(summary)
        archive[symbol]=rows
    if sum(len(x) for x in archive.values())>MAX_EXPORT_ROWS:
        raise ValueError("archive_row_cap_exceeded")
    counts=Counter()
    for x in summaries:
        for k in ("revisions_examined","current_rolling_rows","recoverable_unconflicted_rows",
                  "recovered_not_in_current_rolling_window","conflicting_timestamp_rows_excluded"):
            counts[k]+=x[k]
    result={
        "schema":"remura-v205-public-retail-git-revision-recovery",
        "source_repository":"mirkoworz/remura",
        "source_pinned_main_sha":PINNED_MAIN,
        "snapshot_format":"public Myfxbook Community Outlook history/records",
        "symbols_count":len(paths),
        "totals":dict(counts),
        "symbols":summaries,
        "source_is_public_only":True,
        "cloudflare_requests":0,"provider_requests":0,
        "git_commit_dates_are_independent_provider_first_seen":False,
        "historical_trade_signal_eligibility_inferred":False,
        "profit_or_alpha_calculated":False,
        "no_production_mutation":True,
        "all_revisions_within_retained_git_history_only":True,
        "archive": "NOT_EXPORTED" if export is None else "PUBLIC_JSON_GZIP_LOCAL_ONLY",
    }
    if export is not None:
        export.parent.mkdir(parents=True,exist_ok=True)
        payload={
            "schema":"remura-v205-public-retail-rows-with-git-revision-metadata",
            "source_pinned_main_sha":PINNED_MAIN,
            "recovered_public_history":archive,
            "not_independent_provider_first_seen":True,
            "no_price_outcomes_or_institutional_ownership":True,
        }
        with gzip.open(export,"wt",encoding="utf-8",compresslevel=9) as h:
            json.dump(payload,h,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(",",":"))
    return result


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--export",type=Path)
    ap.add_argument("--manifest",type=Path)
    args=ap.parse_args()
    report=audit(args.repo,export=args.export)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True,exist_ok=True)
        args.manifest.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print("REMURA_V205_PUBLIC_RETENTION_PROOF="+json.dumps({
        "source_sha":report["source_pinned_main_sha"],"symbols":report["symbols_count"],
        **report["totals"],
        "symbols_with_conflicts":[x["symbol"] for x in report["symbols"] if x["conflicting_timestamp_rows_excluded"]>0],
        "alpha":False,"provider_calls":0,"cloudflare_calls":0},sort_keys=True))


if __name__=="__main__":
    main()
