#!/usr/bin/env python3
"""REMURA Track B A/B: isolate redundant OHLC source attestation overhead.

A is the current compact scanner plus the OLD redundant full-document digest
for every symbol, B is the optimized compact scanner. Same fixture, same
clock, isolated SQLite clones, ABBA order on ONE GitHub-hosted runner. The
benchmark is synthetic and does not measure Oracle or trading outcomes.
"""
from __future__ import annotations

from contextlib import nullcontext
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))

import signals_monitor as live
from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_universe as universe
from test_shark_staging_scan import fixture, clone, standard_state, NOW

PREFIX="REMURA_TRACK_B_PAIRED_DIGEST_CPU="


def run_once(path, legacy_double_digest):
    original=universe.prepare
    def old_prepare(db,**kwargs):
        # Exactly the redundant canonicalized-source validation from the
        # previous implementation, before its already-mandatory _source().
        universe._document_digest(db,kwargs["symbol"],kwargs["observed_document"])
        return original(db,**kwargs)
    change=(patch.object(universe,"prepare",side_effect=old_prepare)
            if legacy_double_digest else nullcontext())
    with patch.object(witness,"_clock",return_value=NOW+timedelta(seconds=2)):
        with change:
            cpu=time.process_time()
            elapsed=time.perf_counter()
            result=live.scan_once_with_compact_price_only_research(path,NOW)
            cpu=time.process_time()-cpu
            elapsed=time.perf_counter()-elapsed
    with sqlite3.connect(path) as db:
        batch=db.execute(
            "SELECT payload_sha256, payload_zlib FROM research_price_only_batches"
        ).fetchone()
    if batch is None:
        raise RuntimeError("missing_synthetic_compact_batch")
    details=result["priceOnlyResearch"]
    if (details["storedMarkets"]!=34 or
            details["eligiblePriceCandidates"]!=34 or
            details["snapshotVersionValidated"] is not True or
            details["extraBrokerRequests"]!=0):
        raise RuntimeError("synthetic_market_denominator_not_equivalent")
    return {
        "cpuSeconds":round(cpu,4),
        "wallSeconds":round(elapsed,4),
        "batchSha":batch[0],
        "compressedBytes":len(batch[1]),
        "legacy":standard_state(path),
        "result":{key:value for key,value in result.items()
                  if key!="priceOnlyResearch"},
    }


def main():
    with tempfile.TemporaryDirectory(prefix="remura-paired-digest-") as root:
        directory=Path(root)
        seed=directory/"seed.sqlite"
        fixture(seed,with_cot=False,all_priced=True,m15_count=4000)
        measurements={"redundant":[],"reused":[]}
        # ABBA pairs reduce drift from cache warmup and runner scheduling.
        order=("redundant","reused","reused","redundant")
        baseline=None
        for index,mode in enumerate(order):
            path=directory/("run%d.sqlite" % index)
            clone(seed,path)
            observation=run_once(path,legacy_double_digest=mode=="redundant")
            signature=(observation["batchSha"],observation["compressedBytes"],
                       observation["legacy"],observation["result"])
            if baseline is None:
                baseline=signature
            elif baseline!=signature:
                raise RuntimeError("digest_or_squalincome_regression")
            measurements[mode].append(observation)
        mean=lambda a:round(sum(x["cpuSeconds"] for x in a)/len(a),4)
        old=mean(measurements["redundant"])
        new=mean(measurements["reused"])
        output={
            "schema":"remura-track-b-paired-digest-cpu-v1",
            "markets":34,"m15BarsPerMarket":4000,
            "comparison":"old_redundant_digest_vs_reused_source_proof",
            "order":"ABBA_same_GitHub_runner",
            "redundantCpuMeanSeconds":old,
            "reusedCpuMeanSeconds":new,
            "cpuRatioOldOverNew":round(old/max(new,0.001),3),
            "redundantCpuSamples":[x["cpuSeconds"]
                                  for x in measurements["redundant"]],
            "reusedCpuSamples":[x["cpuSeconds"]
                                for x in measurements["reused"]],
            "bytewiseSameCompactBatch":True,
            "sameSqualincomeTables":True,
            "sourceVersionValidated":True,
            "newBrokerCalls":0,"oracleMeasured":False,
            "tradingEdgeProven":False,
        }
        print(PREFIX+json.dumps(output,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    main()
