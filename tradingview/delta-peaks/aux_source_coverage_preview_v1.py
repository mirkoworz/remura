#!/usr/bin/env python3
# REMURA v0.8.57 LAB — 14/11/2026 11:47 CET
"""Optional read-only B CVD audit bridge. Its denominator is B, never TV.
No private HMAC output or source IDs. Missing proofs are unknown, not negative.
"""
import sqlite3

SCHEMA="remura-track-b-cot-price-cvd-exact-snapshot-triage-v1"
def coverage(main, private, *, as_of_utc, days, secret):
    for db in (main,private):
        if not isinstance(db,sqlite3.Connection) or db.execute("PRAGMA query_only").fetchone()[0]!=1:
            raise ValueError("query_only_snapshot_required")
    if main is private:
        raise ValueError("separate_cvd_snapshot_required")
    from scripts import shark_cvd_cot_price_triage
    report=shark_cvd_cot_price_triage.audit(main,private,as_of=as_of_utc,days=days,secret=secret)
    if report.get("schema")!=SCHEMA:
        raise ValueError("unexpected_cvd_schema")
    fields=("validLocalCotPricePairs","minimumSignalsWithVerifiedCVD","distinctSignalsWithAnyVerifiedCVD",
            "distinctSignalsWithExactCVD","distinctSignalsWithEarlierCVD")
    result={k:report.get(k) for k in fields}
    for v in result.values():
        if v is not None and (type(v) is not int or v<0):
            raise ValueError("invalid_cvd_count")
    n=result["validLocalCotPricePairs"]
    if n is not None and any(v is not None and v>n for k,v in result.items() if k!="validLocalCotPricePairs"):
        raise ValueError("cvd_denominator_mismatch")
    result.update(status=report["status"],denominator="B_COT_PRICE_PAIRS_NOT_TV",
                  same_tv_decision_proven=False,missing_is_negative=False,
                  cross_database_atomic=False,orders_enabled=False)
    return result
