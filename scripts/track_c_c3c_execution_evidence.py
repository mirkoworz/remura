"""REMURA Track C3c-b: OFFLINE execution evidence, not a market-data witness.

Reconcile GitHub Actions *run metadata* against NOMINAL Myfxbook cron ticks.
A run proves a workflow was observed. Neither created_at nor run_started_at
proves which cron tick triggered it, and success is NOT evidence Myfxbook
published fresh data. Unobserved cron ticks are UNKNOWN, never proven misses
when API pagination, disabled workflow and GitHub scheduling aren't attested.

Separately inspect a TEMPORARY copy of existing opt-in batch_timing SQLite
telemetry through a read-only connection. These rows provide a RETURN upper
bound after cTrader batch ingest, NOT a per-symbol commit, network response,
or provider timestamp. No REST requests, imports of private_server, calls
to Myfxbook/cTrader/CFTC, live database access, jobs or notifications.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
import sqlite3
import tempfile

MODE = "OFFLINE_SYNTHETIC_C3C_EXECUTION_METADATA_AUDIT_ONLY"
BATCH_FILE = "track-c3c-synthetic-batch-timing.sqlite3"
WORKFLOW = ".github/workflows/myfxbook.yml"
UTC = timezone.utc
SLOTS = (7,27,47)
MAX_RUNS = 150
MAX_WINDOW = timedelta(hours=24)
MAX_BATCH_ROWS = 256
MAX_BATCH_SECONDS = 7200


def _clock(value):
    if type(value) is not str or len(value)>36:
        raise ValueError("explicit_utc_timestamp_required")
    if not (value.endswith("Z") or value.endswith("+00:00")):
        raise ValueError("utc_only_timestamp_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z","+00:00"))
    except (ValueError,OverflowError) as exc:
        raise ValueError("invalid_utc_timestamp") from exc
    if parsed.utcoffset()!=timedelta(0):
        raise ValueError("utc_only_timestamp_required")
    return parsed.astimezone(UTC)


def _window(start,end,at):
    first,last,now = map(_clock,(start,end,at))
    if (first.second or first.microsecond or last.second or last.microsecond
            or not timedelta(0)<last-first<=MAX_WINDOW
            or now<last or now-last>timedelta(days=3)):
        raise ValueError("bounded_completed_utc_window_required")
    return first,last,now


def reconcile_github_runs(rows, *, window_start, window_end, observed_at,
                          mode=None):
    """No per-slot execution attribution, even if time-compatible.

    Accept only an allowlisted adapter shape from caller's read-only GitHub
    Actions metadata, not its raw API response. No pagination completeness
    claim. A re-run of the same workflow run counts as ONE observed run.
    """
    if mode!=MODE:
        raise ValueError("explicit_offline_execution_metadata_mode_required")
    first,last,now = _window(window_start,window_end,observed_at)
    if type(rows) is not list or len(rows)>MAX_RUNS:
        raise ValueError("bounded_actions_metadata_list_required")
    allowed={"id","workflow_path","event","head_branch","created_at",
             "run_started_at","status","conclusion","run_attempt"}
    required=allowed-{"run_started_at"}
    cleaned={}
    ignored=0
    for raw in rows:
        if type(raw) is not dict or not required<=raw.keys() or not raw.keys()<=allowed:
            raise ValueError("unexpected_actions_metadata_shape")
        if type(raw["id"]) is not int or raw["id"]<=0:
            raise ValueError("invalid_actions_workflow_run_id")
        if (type(raw["run_attempt"]) is not int
                or not 1<=raw["run_attempt"]<=20):
            raise ValueError("invalid_actions_attempt")
        if (raw["event"]!="schedule" or
                raw["workflow_path"]!=WORKFLOW or raw["head_branch"]!="main"):
            ignored+=1
            continue
        created=_clock(raw["created_at"])
        if created>now:
            raise ValueError("future_actions_run_metadata")
        started=raw.get("run_started_at")
        if started is not None:
            started=_clock(started)
            if started<created or started>now:
                raise ValueError("actions_start_precedes_creation_or_future")
        if raw["status"] not in (
                "completed","queued","in_progress","waiting","pending","requested"):
            raise ValueError("invalid_actions_run_status")
        conclusion=raw["conclusion"]
        if raw["status"]=="completed":
            if conclusion not in ("success","failure","cancelled","timed_out",
                                  "skipped","neutral","action_required","stale"):
                raise ValueError("invalid_actions_completion")
        elif conclusion is not None:
            raise ValueError("incomplete_actions_must_not_have_conclusion")
        candidate=(raw["run_attempt"],created,started,
                   raw["status"],conclusion)
        existing=cleaned.get(raw["id"])
        if existing is not None:
            if candidate[0]==existing[0] and candidate!=existing:
                raise ValueError("conflicting_same_attempt_metadata")
            if candidate[0]<existing[0]:
                continue
        cleaned[raw["id"]]=candidate

    expected=[]
    cursor=first.replace(minute=0,second=0,microsecond=0)
    while cursor<last:
        for minute in SLOTS:
            slot=cursor.replace(minute=minute)
            if first<=slot<last:
                expected.append(slot)
        cursor+=timedelta(hours=1)
    seen=[row for row in cleaned.values() if first<=row[1]<last]
    # Mere time proximity to a cron is NOT a link to that particular run
    # (GitHub can delay, drop and resume scheduled workflows).
    close=0
    lag_seconds=[]
    for _,created,_,_,_ in seen:
        candidates=[(created-slot).total_seconds() for slot in expected
                    if timedelta(0)<=created-slot<timedelta(minutes=20)]
        if candidates:
            close+=1
            lag_seconds.append(int(min(candidates)))
    success=sum(x[4]=="success" for x in seen)
    failed=sum(x[4] in ("failure","timed_out","cancelled","action_required")
               for x in seen)
    running=sum(x[3]!="completed" for x in seen)
    return {
        "schema":"remura-track-c3c-actions-metadata-v1",
        "state":"OBSERVED_GITHUB_WORKFLOW_METADATA_NOT_PROVIDER_FRESHNESS",
        "nominalCronSlots":len(expected),
        "observedScheduledRuns":len(seen),
        "completedSuccessRuns":success,
        "completedFailedOrCancelledRuns":failed,
        "uncompletedRuns":running,
        "temporallyCompatibleRunsNotSlotProof":close,
        "minCompatibleStartLagSeconds":min(lag_seconds) if lag_seconds else None,
        "maxCompatibleStartLagSeconds":max(lag_seconds) if lag_seconds else None,
        "otherEventOrWorkflowRowsIgnored":ignored,
        "observedRunsWithoutCompatibleNominalSlot":len(seen)-close,
        "nominalSlotsWithoutProvenRunIdentity":len(expected),
        "provenSkippedCronSlots":0,
        "runToCronSlotIdentityProvable":False,
        "apiPaginationAndRunHistoryCompleteProven":False,
        "workflowEnabledThroughoutWindowProven":False,
        "actionsSucceededMeansFreshMyfxbook":False,
        "marketDataProviderPublicationVerified":False,
        "liveRuntimeObservedByThisTest":False,
        "actualTradingEdge":False,
        "newExternalApiCalls":0,
    }


def _batch_path(path):
    if not isinstance(path,(str,Path)):
        raise ValueError("explicit_synthetic_batch_file_required")
    p=Path(path).absolute()
    root=Path(tempfile.gettempdir()).resolve()
    parent=p.parent.resolve()
    if (p.is_symlink() or p.parent.is_symlink() or
            p.name!=BATCH_FILE or parent.parent!=root or
            not parent.name.startswith("remura-c3c-runtime-")
            or not parent.is_dir() or p.resolve().parent!=parent):
        raise ValueError("only_disposable_batch_timing_file_allowed")
    return p


def inspect_batch_timing(path, *, observed_at, mode=None):
    """Read-only, bounded analysis of existing telemetry schema, if present.

    Never infer absent telemetry means no real cTrader batches; the source
    can be disabled, its timing opt-in can be OFF, or older rows pruned.
    """
    if mode!=MODE:
        raise ValueError("explicit_offline_execution_metadata_mode_required")
    now=_clock(observed_at)
    p=_batch_path(path)
    base={
        "schema":"remura-track-c3c-batch-metadata-v1",
        "state":"UNKNOWN_NO_TELEMETRY",
        "batchRowsObserved":None,
        "scheduledSymbolsInObservedBatches":None,
        "savedSymbolsInObservedBatches":None,
        "zeroSavedBatches":None,
        "failedPostIngestScans":None,
        "postIngestNotRun":None,
        "latestBatchFinishedAt":None,
        "perSymbolCommitWitnessed":False,
        "allRuntimeBatchesObserved":False,
        "sourceWasReadOnly":True,
        "actualMarketOHLCInspected":False,
        "newExternalApiCalls":0,
    }
    if not p.is_file():
        return base
    try:
        db=sqlite3.connect(
            "file:"+quote(str(p),safe="/")+"?mode=ro",uri=True,timeout=.025)
        try:
            db.execute("PRAGMA query_only=ON")
            if len(db.execute("PRAGMA database_list").fetchall())!=1:
                raise ValueError("attached_batch_database_not_allowed")
            rows=db.execute(
                "SELECT started_utc,ingest_returned_utc,finished_utc,"
                "slot,scheduled_markets,saved_markets,batch_elapsed_ms,"
                "post_scan_state,post_scan_lag_ms "
                "FROM remura_batch_timing ORDER BY id DESC LIMIT ?",
                (MAX_BATCH_ROWS+1,)
            ).fetchall()
        finally:
            db.close()
        if not rows or len(rows)>MAX_BATCH_ROWS:
            return base
        for started,returned,finished,slot,planned,saved,elapsed,state,lag in rows:
            a,b,c=map(_clock,(started,returned,finished))
            if (not a<=b<=c<=now
                    or c-a>timedelta(seconds=MAX_BATCH_SECONDS)
                    or type(slot) is not int or not 1<=slot<=8
                    or type(planned) is not int or not 1<=planned<=8
                    or type(saved) is not int or not 0<=saved<=planned
                    or type(elapsed) is not int or elapsed<0
                    or abs(elapsed-(b-a).total_seconds()*1000)>2
                    or state not in ("ok","failed","not_run")
                    or ((state=="not_run")!=(lag is None))
                    or (lag is not None and
                        (type(lag) is not int or lag<0
                         or lag>(c-b).total_seconds()*1000+2))):
                raise ValueError("invalid_original_batch_runtime_telemetry")
        return {
            **base,
            "state":"OFFLINE_TEMP_COPY_OF_EXISTING_BATCH_TELEMETRY",
            "batchRowsObserved":len(rows),
            "scheduledSymbolsInObservedBatches":sum(x[4] for x in rows),
            "savedSymbolsInObservedBatches":sum(x[5] for x in rows),
            "zeroSavedBatches":sum(x[5]==0 for x in rows),
            "failedPostIngestScans":sum(x[7]=="failed" for x in rows),
            "postIngestNotRun":sum(x[7]=="not_run" for x in rows),
            "latestBatchFinishedAt":max(_clock(x[2]) for x in rows).isoformat(),
        }
    except (sqlite3.Error,ValueError,OSError,TypeError):
        return {**base,"state":"UNKNOWN_INVALID_OR_UNAVAILABLE_TELEMETRY"}
