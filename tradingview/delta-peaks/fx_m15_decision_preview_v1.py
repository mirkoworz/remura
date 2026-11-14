#!/usr/bin/env python3
# REMURA v0.8.55 LAB — 14/11/2026 11:44 CET
"""Offline candidate joining a declared Track B decision link to its exact M5 close.
Never reads B's database or claims the supplied link is authentic.
B link schema follows shark_signal_ingest_decision_link.py at 8dc51e8a.
No trading, network, writes, price comparison across feeds or future evidence.
"""
from datetime import datetime, timezone, timedelta
import re
from fx_asof_handoff_v1 import handoff

ALGORITHM="original_same_snapshot_ingest_cot_price_v1"
FIELDS={"history_id","symbol","cot_report_date","price_closed_at_utc",
        "observed_at_utc","linked_at_utc","original_ingest_proof_id",
        "merged_document_sha256","cot_source_version_digest","algorithm"}
HEX=re.compile(r"[0-9a-f]{64}\Z")
EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)

def utc(s):
    if type(s) is not str or len(s)>48:
        raise ValueError("bad_utc")
    try:
        d=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError:
        raise ValueError("bad_utc") from None
    if d.tzinfo is None or d.utcoffset()!=timedelta(0):
        raise ValueError("utc_required")
    return d

def ms(d):
    return (d-EPOCH)//timedelta(milliseconds=1)

def preview(link,rows,*,audit_asof_utc):
    if type(link) is not dict or set(link)!=FIELDS:
        raise ValueError("bad_b_link_shape")
    if link["symbol"]!="EURUSD" or link["algorithm"]!=ALGORITHM:
        raise ValueError("wrong_b_cohort_or_algorithm")
    for field in ("history_id","original_ingest_proof_id"):
        if type(link[field]) is not int or link[field]<=0:
            raise ValueError("bad_b_identifier")
    for field in ("merged_document_sha256","cot_source_version_digest"):
        if type(link[field]) is not str or not HEX.fullmatch(link[field]):
            raise ValueError("bad_b_hash")
    closed=utc(link["price_closed_at_utc"])
    observed=utc(link["observed_at_utc"])
    linked=utc(link["linked_at_utc"])
    audit=utc(audit_asof_utc)
    if closed.minute%15 or closed.second or closed.microsecond:
        raise ValueError("not_m15_close")
    if not closed<=observed<=linked<=audit or observed-closed>timedelta(minutes=3) or linked-observed>timedelta(seconds=30):
        raise ValueError("bad_b_clock")
    # Same close only. Floor decision microseconds: receipt clocks have ms resolution.
    tv=handoff(rows,decision_ms=ms(observed),bar_close_ms=ms(closed))
    return {
        "schema":"remura.tv.b.m15.link.preview.v1","version":"0.8.55-lab",
        "status":"DESCRIPTIVE_PAIR_CANDIDATE" if tv["candidate"] is not None else "TV_NOT_ADMITTED",
        "tv_status":tv["status"],"tv_candidate":tv["candidate"] is not None,
        "tv_excluded_counts":tv["excluded_counts"],
        "decision_close_ms":ms(closed),"decision_ms":ms(observed),
        "source_mapping":"B_EURUSD_M15_TO_TV_FXCM_EURUSD_M5_EXACT_CLOSE",
        "b_link_provenance":"CALLER_DECLARATION_NOT_INDEPENDENTLY_VERIFIED",
        "b_link_created_after_or_at_decision":True,
        "cot_values_verified":False,"cvd_verified":False,"retail_verified":False,
        "cross_feed_price_equivalence_assumed":False,
        "institutional_admissible":False,"predictive_admissible":False,
        "track_b_connected":False,"orders_enabled":False,"notifications_enabled":False,
    }
