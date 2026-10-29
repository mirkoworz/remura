#!/usr/bin/env python3
"""REMURA v1.49: read-only weekly CFTC ingestion health.

Never infer CFTC publication times from Tuesday report dates. "First seen"
means LOCAL first successful capture, not official availability. All alerts
are diagnostic; late public reports/holidays can be legitimate.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from collections import defaultdict
from pathlib import Path

from cot_monitor import DATASETS
from price_feed import UTC, parse_time, utcnow

MAX_WEEKS_SHOWN=6
REVIEW_REPORT_AGE_DAYS=14
RECENT_CAPTURE_HOURS=48


def _timestamp(value, now):
    if not value:
        return None
    try:
        parsed=parse_time(value).astimezone(UTC)
        if parsed<=now:
            return parsed
    except (TypeError, ValueError, OverflowError, AttributeError):
        pass
    return None


def _date(value, now):
    try:
        parsed=dt.date.fromisoformat(value)
        return parsed if parsed<=now.date() else None
    except (TypeError, ValueError, OverflowError):
        return None


def _status(db, now, enabled):
    tables={row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND "
        "name IN ('cot_reports','cot_first_seen','status')")}
    state={}
    if "status" in tables:
        state=dict(db.execute(
            "SELECT key,value FROM status WHERE key LIKE 'cot_%'"))
    # Read only the 14 PUBLIC approved contracts.
    expected={kind:set(config["codes"]) for kind,config in DATASETS.items()}
    by_week=defaultdict(lambda:defaultdict(set))
    if "cot_reports" in tables:
        for kind,code,week in db.execute(
            "SELECT dataset,code,report_date FROM cot_reports"):
            if kind in expected and code in expected[kind] and _date(week,now):
                by_week[week][kind].add(code)
    weeks=sorted(by_week,reverse=True)
    tracked={}
    if "cot_first_seen" in tables:
        # Records are small (~14 per week); avoid database creation/writes.
        for kind,code,week,stamp in db.execute(
            "SELECT dataset,code,report_date,first_seen_at FROM cot_first_seen"):
            if kind in expected and code in expected[kind] and _date(week,now):
                tracked[(kind,code,week)]=stamp

    def counts(kind,week):
        present=by_week[week].get(kind,set())
        observed=0
        recent=0
        invalid=0
        for code in present:
            stamp=tracked.get((kind,code,week))
            if stamp is None:
                continue
            parsed=_timestamp(stamp,now)
            if parsed is None:
                invalid+=1
                continue
            observed+=1
            if now-dt.timedelta(hours=RECENT_CAPTURE_HOURS)<=parsed:
                recent+=1
        return observed,recent,invalid

    combined=[week for week in weeks
              if all(by_week[week].get(kind,set())==codes
                     for kind,codes in expected.items())]
    latest_common=combined[0] if combined else None
    previous_common=combined[1] if len(combined)>1 else None
    week_records=[]
    for week in weeks[:MAX_WEEKS_SHOWN]:
        groups={}
        for kind,need in expected.items():
            found=by_week[week].get(kind,set())
            known,recent,invalid=counts(kind,week)
            groups[kind]={
                "present":len(found),"expected":len(need),
                "missingCodes":sorted(need-found),
                "firstSeenKnown":known,
                "firstSeenUnknown":len(found)-known-invalid,
                "invalidFirstSeen":invalid,
                "recentlyCapturedRows48h":recent,
            }
        week_records.append({
            "cotWeek":week,
            "complete":all(not d["missingCodes"] for d in groups.values()),
            "datasets":groups,
        })

    dataset_results={}
    for kind,need in expected.items():
        latest=next((week for week in weeks if by_week[week].get(kind)),None)
        # Compute latest coverage independently of the six-week UI window.
        present=by_week[latest].get(kind,set()) if latest else set()
        known,recent,invalid=counts(kind,latest) if latest else (0,0,0)
        # Last attempt/success must be in UTC and must never lie in the future.
        success=_timestamp(state.get("cot_"+kind+"_last_success"),now)
        last_attempt=_timestamp(state.get("cot_last_attempt"),now)
        source_state=state.get("cot_"+kind+"_state","not_collected")
        age=(now.date()-dt.date.fromisoformat(latest)).days if latest else None
        stats={
            "present":len(present),"expected":len(need),
            "missingCodes":sorted(need-present),
            "firstSeenKnown":known,"firstSeenUnknown":len(present)-known-invalid,
            "invalidFirstSeen":invalid,
            "recentlyCapturedRows48h":recent,
        }
        if not enabled:
            verdict="disabled"
        elif not latest:
            verdict="no_data"
        elif stats["missingCodes"]:
            verdict="incomplete"
        elif stats["invalidFirstSeen"]:
            verdict="timestamp_review"
        elif source_state=="error":
            verdict="source_error"
        elif age is not None and age>REVIEW_REPORT_AGE_DAYS:
            verdict="age_review"
        elif source_state=="ok" and success:
            verdict="ok"
        else:
            verdict="status_review"
        dataset_results[kind]={
            "state":verdict,"latestCotWeek":latest,
            "reportAgeDays":age,"collectorState":source_state if source_state in
               ("ok","error","not_collected") else "unknown",
            "lastCollectorAttemptUtc":last_attempt.isoformat() if last_attempt else None,
            "lastSuccessUtc":success.isoformat() if success else None,
            **stats,
        }

    # Mark local acquisition only when BOTH datasets have the same
    # COMPLETE newest report week and show newly captured rows on each.
    same_latest=(dataset_results["tff"]["latestCotWeek"] is not None and
        dataset_results["tff"]["latestCotWeek"]==
        dataset_results["disagg"]["latestCotWeek"])
    latest_week=dataset_results["tff"]["latestCotWeek"] if same_latest else None
    acquired_recently=bool(
        same_latest and latest_week==latest_common and
        all(dataset_results[kind]["recentlyCapturedRows48h"]>0
            for kind in expected)
    )
    healthy=enabled and all(v["state"]=="ok" for v in dataset_results.values())
    status=("disabled" if not enabled else
            "waiting" if not weeks else
            "ready" if healthy and same_latest else "attention")
    return {
        "schema":"remura-cot-week-watch-v1",
        "mode":"diagnostic_only",
        "collectorCadenceHours":6,
        "officialReleaseTimeVerified":False,
        "captureMeans":"first_local_capture_not_publication",
        "enabled":bool(enabled),
        "status":status,
        "expectedContracts":sum(map(len,expected.values())),
        "latestCommonCompleteWeek":latest_common,
        "previousCommonCompleteWeek":previous_common,
        "hasTwoCompleteReferenceWeeks":bool(previous_common),
        "latestWeekLocallyCapturedIn48h":acquired_recently,
        "datasets":dataset_results,
        "weeks":week_records,
        "notes":"Nessuna data di pubblicazione CFTC ricostruita. "
                "Report vecchi senza prima acquisizione rimangono sconosciuti. "
                "Ritardi e festività richiedono verifica, non implicano dati persi. "
                "Nessun segnale né ordine.",
    }


def cot_week_watch_status(db_path, enabled, now=None):
    now=(now or utcnow()).astimezone(UTC)
    path=Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Archivio REMURA non trovato")
    db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        return _status(db,now,bool(enabled))
    finally:
        db.close()
