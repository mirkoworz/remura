#!/usr/bin/env python3
"""REMURA A v21.5 LAB — one-command PRIVATE OFFLINE M15 scientific readiness.

ONLY reuse the existing V20.4 real-receipt proof and cTrader M15 read-only
coverage engine. Never query broker, Cloudflare, collector or network.
No prices, broker identifiers, database paths, secrets, or trading signals
are written or printed. A copy of private SQLite is required for real coverage.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from v204_private_cvd_price_coverage import assess, read_local_price_db, utc

UTC=timezone.utc
VERSION="A_V21_5_LAB"
SCHEMA="remura-a-offline-price-readiness-v1"
PROOF=Path(__file__).resolve().parent/"real-proofs"/"REMURA-V203-CVD-TEST-RECEIPTS-20261123.json"


def probe(offline_sqlite: Path | None, *, as_of: datetime) -> dict:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of_must_be_UTC")
    proof=json.loads(PROOF.read_text("utf-8"))
    prices=read_local_price_db(offline_sqlite) if offline_sqlite is not None else None
    report=assess(proof, prices, as_of=as_of)
    horizons={}
    for key in ("60m","4h","24h"):
        item=report["horizons"][key]
        horizons[key]={
            "coverageCompleteM15Cohorts":item["complete_unique_m15_price_cohorts"],
            "closedButPriceMissingCohorts":item["closed_but_price_missing_unique_cohorts"],
            "notYetMatureCohorts":item["not_yet_mature_unique_cohorts"],
            "totalDistinctCohorts":item["total_unique_cohorts"],
        }
    complete=sum(x["coverageCompleteM15Cohorts"] for x in horizons.values())
    return {
        "schema":SCHEMA,"version":VERSION,
        "asOfUtc":report["as_of_utc"],
        "status":(
            "AWAITING_LOCAL_PRIVATE_SQLITE_COPY" if prices is None
            else "COVERAGE_FOUND_DIRECTION_NOT_ATTESTED" if complete
            else "PRICE_COPY_CHECKED_NO_COMPLETE_HORIZON"
        ),
        "existingRealCvdTestReceipts":12,
        "independentTestReceiptM15EntryCohorts":4,
        "allTestReceiptsObservationOnly":True,
        "numberOfAdmittedProspectiveDecisions":0,
        "pricesAvailableFromPrivateCopy": prices is not None,
        "priceFeedIndependentlyAuthenticated":False,
        "cvdSourceIndependentlyAuthenticated":False,
        "futureDirectionalReturnsComputed":False,
        "realCostsObserved":False,
        "alphaVerified":False,
        "networkCalls":0,"filesWritten":0,
        "horizons":horizons,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-sqlite",type=Path,
                        help="An existing OFFLINE private cTrader SQLite copy, NOT live DB")
    parser.add_argument("--as-of-utc",type=str,
                        help="Optional explicit clock ending in Z; normally current UTC")
    parser.add_argument("--confirm-offline-copy",action="store_true",
                        help="Confirm the SQLite file is a safe offline COPY, not the live collector")
    args=parser.parse_args()
    if args.offline_sqlite is not None and not args.confirm_offline_copy:
        parser.error("Use only a confirmed offline SQLite copy; no live collector")
    if args.confirm_offline_copy and args.offline_sqlite is None:
        parser.error("offline SQLite copy path required")
    try:
        now=utc(args.as_of_utc) if args.as_of_utc else datetime.now(UTC)
        if now > datetime.now(UTC)+timedelta(minutes=5):
            raise ValueError("future_as_of_rejected")
        report=probe(args.offline_sqlite,as_of=now)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        parser.error("Offline proof/price source rejected; private details withheld")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
