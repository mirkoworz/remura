"""Offline bounded REMURA Track B CVD M15-prefix incremental resource probe.

Compares the same genuine synthetic COT+OHLC evidence write with/without
the OPTIONAL M15 prefix, and the same private CVD event write with/without
prospective source/HMAC/prefix proof. All databases are SQLite :memory:
copies of one synthetic reference. No LIVE, cTrader, Oracle, Firestore,
secrets in output, user inputs, network, scheduler, or persisted artefacts.

Timing is local CI runner MICROBENCHMARK, NOT a forecast of Oracle ingest
contention. Storage is SQLite page counts, not actual block/volume billing.
No performance threshold is claimed from CI. All accuracy gates must pass.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import resource
import sqlite3
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
# Direct "python scripts/<tool>.py" starts with scripts/ on sys.path,
# unlike unittest from repository root. Add the package parent explicitly.
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))

from scripts import shark_cvd_ledger as cvd
from scripts import shark_cvd_prefix_lineage as prefix
from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from test_shark_cvd_cot_price_triage import (
    source_with_verified_divergence, original_cvd_event,
)
from test_shark_observation_bundle import create
from test_shark_signal_evidence import insert_history,AT,NOW,OBSERVED,iso
from test_shark_cvd_ledger import QUALITY,SECRET

MAX_PAIRS=12
SCOPE = "OFFLINE_SYNTHETIC_MICROBENCHMARK_NOT_LIVE_ORACLE"


def _percentile(data, fraction):
    ordered=sorted(data)
    return round(ordered[max(0,min(len(ordered)-1,math.ceil(
        len(ordered)*fraction)-1))],4)


def _stats(samples):
    return {
        "n":len(samples),
        "medianWallMs":round(statistics.median(x[0] for x in samples),4),
        "p95WallMs":_percentile([x[0] for x in samples],.95),
        "medianCpuMs":round(statistics.median(x[1] for x in samples),4),
        "p95CpuMs":_percentile([x[1] for x in samples],.95),
        "medianPageBytes":round(statistics.median(x[2] for x in samples)),
    }


def _db_size(db):
    return (db.execute("PRAGMA page_count").fetchone()[0] *
            db.execute("PRAGMA page_size").fetchone()[0])


def _timed(fn):
    cpu0=time.process_time_ns()
    wall0=time.perf_counter_ns()
    result=fn()
    wall=(time.perf_counter_ns()-wall0)/1e6
    cpu=(time.process_time_ns()-cpu0)/1e6
    return result,wall,cpu


def probe(*,pairs=8):
    """Return privacy-safe aggregate metrics, raising for any failed gate."""
    if type(pairs) is not int or not 2<=pairs<=MAX_PAIRS:
        raise ValueError("bounded_microbenchmark_pairs_required")
    base,doc=create()
    main_times={False:[],True:[]}
    private_times={False:[],True:[]}
    first_counts={}
    rows_added={}
    try:
        source_with_verified_divergence(base,doc)
        doc=json.loads(base.execute(
            "SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0])
        ev=original_cvd_event(doc)
        witness.witness(base,clock=AT)
        for k in range(pairs):
            # Balanced A-B/B-A; no benchmark result used as a pass gate.
            order=(False,True) if k%2==0 else (True,False)
            for on in order:
                main=sqlite3.connect(":memory:")
                base.backup(main)
                try:
                    def do_main():
                        with main:
                            history_id=insert_history(main)
                            return bundle.record(
                                main,history_id=history_id,
                                observed_document=doc,clock=NOW,
                                capture_cvd_prefix=on)
                    outcome,wall,cpu=_timed(do_main)
                    if outcome["state"]!="BOTH_LOCAL_PROOFS_PRESENT":
                        raise ValueError("missing_original_cot_price_witness")
                    expected=("FUTURE_ORIGINAL_M15_PREFIXES_RECORDED"
                              if on else "OFF")
                    if outcome["cvdSessionPrefixProof"]!=expected:
                        raise ValueError("incorrect_prefix_write_gate")
                    count=0
                    if on:
                        count=main.execute(
                            f"SELECT count(*) FROM {prefix.MAIN_TABLE}"
                            ).fetchone()[0]
                        if not 1<=count<=prefix.MAX_CUTOFFS:
                            raise ValueError("main_prefix_bound_invalid")
                    else:
                        if main.execute(
                                "SELECT 1 FROM sqlite_master WHERE name=?",
                                (prefix.MAIN_TABLE,)).fetchone():
                            raise ValueError("legacy_main_created_prefix_table")
                    if main.execute(
                            "PRAGMA integrity_check").fetchone()[0]!="ok":
                        raise ValueError("main_sqlite_integrity_failed")
                    main_times[on].append((wall,cpu,_db_size(main)))
                    first_counts.setdefault(on,count)
                    if first_counts[on]!=count:
                        raise ValueError("nondeterministic_main_prefix_count")
                finally:
                    main.close()

                private=sqlite3.connect(":memory:")
                try:
                    cvd.ensure_schema(private)
                    def do_private():
                        return cvd.append(
                            private,ev,QUALITY,
                            source_collected_at=iso(OBSERVED),
                            hmac_secret=SECRET,now=OBSERVED,
                            source_document=doc if on else None)
                    outcome,wall,cpu=_timed(do_private)
                    if (outcome["state"]!="RECORDED"
                            or outcome["sourceDocumentBound"] is not on):
                        raise ValueError("private_cvd_gate_broken")
                    if on:
                        n=private.execute(
                            f"SELECT count(*) FROM {prefix.PRIVATE_TABLE}"
                            ).fetchone()[0]
                        if n!=1:
                            raise ValueError("private_prefix_missing")
                    else:
                        n=0
                        if private.execute(
                                "SELECT 1 FROM sqlite_master WHERE name=?",
                                (prefix.PRIVATE_TABLE,)).fetchone():
                            raise ValueError("legacy_private_created_prefix_table")
                    if private.execute(
                            "PRAGMA integrity_check").fetchone()[0]!="ok":
                        raise ValueError("private_sqlite_integrity_failed")
                    private_times[on].append((wall,cpu,_db_size(private)))
                    rows_added.setdefault(on,n)
                    if rows_added[on]!=n:
                        raise ValueError("nondeterministic_private_prefix_count")
                finally:
                    private.close()
        main0,main1=(_stats(main_times[x]) for x in (False,True))
        private0,private1=(_stats(private_times[x]) for x in (False,True))
        return {
            "schema":"remura-track-b-prefix-resource-probe-v1",
            "status":"PASS",
            "scope":SCOPE,
            "pairedRoundsPerMode":pairs,
            "main":{
                "legacy":main0,"optIn":main1,
                "newPrefixRowsPerOriginalSignal":first_counts[True],
                "extraMedianSQLitePageBytes":(
                    main1["medianPageBytes"]-main0["medianPageBytes"]),
                "additionalBrokerCalls":0,
            },
            "private":{
                "legacy":private0,"optIn":private1,
                "newPrefixRowsPerNewCvdEvent":rows_added[True],
                "extraMedianSQLitePageBytes":(
                    private1["medianPageBytes"]-private0["medianPageBytes"]),
                "additionalBrokerCalls":0,
            },
            "pilotMarketsMaximum":len(prefix.PILOT),
            "maxCandidatePrefixesPerOriginalSignal":prefix.MAX_CUTOFFS,
            "mainArchiveCapacityRows":prefix.MAX_MAIN_ROWS,
            "maxHypotheticalPilotRowsPerDayAtOneSignalPer15mPerMarket":(
                len(prefix.PILOT)*96*prefix.MAX_CUTOFFS),
            "hypotheticalDaysToReachCapacityAtThisNonObservedUpperBound":
                round(prefix.MAX_MAIN_ROWS/(
                    len(prefix.PILOT)*96*prefix.MAX_CUTOFFS),2),
            "peakProcessRssKiB":resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss,
            "rssAttributableOnlyToNewFeature":False,
            "performanceOrBillingCertifiedForOracle":False,
            "liveIngestInterferenceTested":False,
            "institutionalEdgeEstablished":False,
            "alertsEnabled":False,
            "ordersEnabled":False,
        }
    finally:
        base.close()


def main():
    result=probe()
    print(json.dumps(result,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    main()
