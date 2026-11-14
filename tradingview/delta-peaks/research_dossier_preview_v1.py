#!/usr/bin/env python3
# REMURA v0.8.75 LAB — 14/11/2026 17:07 CET
"""Read-only research dossier; uses the existing B causal audit, no live wiring.
All source identities are local proofs, not independently authenticated inputs.
No future evidence, prices in the report, execution, orders or notifications.
"""
from collections import Counter, defaultdict
from datetime import timedelta
import sqlite3
from fx_m15_decision_preview_v1 import utc, ms, HEX
from fx_asof_handoff_v1 import handoff
from fx_outcome_readiness_v1 import readiness
from volume_features_v1 import MAX_EXPORT_ROWS, decode
from fx_pilot_config_v1 import REFERENCE, compare_v1_fields
from cvd_squalincome_asof_preview_v1 import join_local_pairs
from cvd_auxiliary_same_decision_preview_v1 import _from_verified_pairs

VERSION = "0.8.75-lab"
B_PIN = "8dc51e8a199dc1cfd45e4cd2e7b339510af2eb2b"
B_SCHEMA = "remura-track-b-causal-local-cot-price-join-v1"

def relation(side, value):
    if value is None:
        return "UNKNOWN"
    if value == 0:
        return "NEUTRAL"
    return "ALIGNED" if side == value else "OPPOSED"

def dossier(db, rows, *, as_of_utc, days=1, origin="LOCAL_SNAPSHOT", cvd_rows=None, auxiliary=False,
            private_cvd_db=None, cvd_secret=None, retail_root=None, retail_authorized_at=None):
    """Caller supplies an explicit query-only SQLite snapshot and D1 export.
    B source must be made available by the isolated, pinned research checkout.
    The adapter does not open a production DB or establish source authenticity.
    """
    if not isinstance(db, sqlite3.Connection) or db.execute("PRAGMA query_only").fetchone()[0] != 1:
        raise ValueError("query_only_snapshot_required")
    if origin not in ("SYNTHETIC","LOCAL_SNAPSHOT"):
        raise ValueError("invalid_origin")
    if type(days) is not int or not 1<=days<=7:
        raise ValueError("invalid_days")
    if not isinstance(rows,list) or len(rows)>MAX_EXPORT_ROWS:
        raise ValueError("invalid_export")
    if type(auxiliary) is not bool or (not auxiliary and any(x is not None for x in
        (private_cvd_db,cvd_secret,retail_root,retail_authorized_at))):
        raise ValueError("explicit_auxiliary_required")
    if auxiliary and (cvd_rows is None or db.in_transaction or
        (private_cvd_db is None)!=(cvd_secret is None) or
        (retail_root is None)!=(retail_authorized_at is None)):
        raise ValueError("auxiliary_scope")
    at=utc(as_of_utc)
    cutoff=ms(at)
    from scripts import shark_causal_pair_audit
    pairs=[]
    b=shark_causal_pair_audit.audit(db,as_of=as_of_utc,days=days,_verified_pairs=pairs)
    if b.get("schema")!=B_SCHEMA:
        raise ValueError("unexpected_b_schema")
    counts=Counter()
    relations={k:Counter() for k in ("cot_vs_intrabar_delta","cot_vs_price_body","cot_vs_footprint_delta")}
    event_counts=Counter()
    seen=set()
    grouped=defaultdict(list)
    window_rows=[]
    lower=ms(at-timedelta(days=days))
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("malformed_export_metadata")
        if row.get("symbol")!="FXCM:EURUSD" or row.get("timeframe")!="5":
            continue
        close,receipt=row.get("bar_close_ms"),row.get("received_at_ms")
        if type(close) is not int or type(receipt) is not int:
            raise ValueError("invalid_fx_export_metadata")
        if receipt<=cutoff and lower<=close<=cutoff:
            grouped[close].append(row)
            window_rows.append(row)
    n=b.get("locallyJoinedCausalPairs")
    if n is None:
        if pairs:
            raise ValueError("unexpected_b_pairs")
    elif type(n) is not int or n!=len(pairs):
        raise ValueError("b_pair_denominator_mismatch")
    for symbol,week,closed_s,observed_s,digest,side in pairs:
        if symbol!="EURUSD":
            counts["OTHER_B_MARKET"]+=1
            continue
        close,observed=utc(closed_s),utc(observed_s)
        if type(side) is not int or side not in (-1,1) or type(digest) is not str or not HEX.fullmatch(digest):
            raise ValueError("invalid_local_pair")
        key=(symbol,week,closed_s,observed_s)
        if key in seen:
            raise ValueError("duplicate_local_pair")
        seen.add(key)
        if not at-timedelta(days=days)<=observed<=at or close>observed:
            raise ValueError("b_pair_outside_asof")
        if close.minute%15 or close.second or close.microsecond or observed-close>timedelta(minutes=3):
            counts["B_DECISION_CLOCK_OUTSIDE_HANDOFF"]+=1
            continue
        tv=handoff(grouped.get(ms(close),[]),decision_ms=ms(observed),bar_close_ms=ms(close))
        candidate=tv["candidate"]
        if candidate is None:
            counts[tv["status"]]+=1
            continue
        # Check exactly the snapshot admitted as of the original decision.
        matched=[r for r in grouped[ms(close)] if r["received_at_ms"]==candidate["received_at_ms"]]
        if not matched or not all(compare_v1_fields(decode(r)[0],REFERENCE)["v1_fields_match"] for r in matched):
            counts["BLOCKED_CONFIG_METADATA_MISMATCH"]+=1
            continue
        counts[tv["status"]]+=1
        o=candidate["observed"]
        relations["cot_vs_intrabar_delta"][relation(side,o["delta_sign"])]+=1
        relations["cot_vs_price_body"][relation(side,o["price_body_sign"])]+=1
        relations["cot_vs_footprint_delta"][relation(side,o["footprint_delta_sign"])]+=1
        event_counts.update(candidate["observed_labels"])
    if sum(counts.values())!=len(pairs):
        raise ValueError("nonconserving_pair_population")
    outcome=readiness(window_rows,as_of_ms=cutoff)
    cvd_join=None if cvd_rows is None or n is None else join_local_pairs(pairs,cvd_rows,as_of_ms=cutoff)
    aux=None if not auxiliary else _from_verified_pairs(db,private_cvd_db,cvd_rows,pairs,n,
        as_of_utc=as_of_utc,days=days,secret=cvd_secret,retail_root=retail_root,authorized_at=retail_authorized_at)
    return {
        "schema":"remura.tv.research.dossier.preview.v1","version":VERSION,
        "origin":origin,"as_of_ms":cutoff,"days":days,
        "b_audit_status":b["status"],"b_local_pairs":n,
        "pair_counts":dict(sorted(counts.items())),
        "relations":{k:dict(sorted(v.items())) for k,v in relations.items()},
        "paired_event_counts":dict(sorted(event_counts.items())),
        "outcomes":outcome,"cot_source":"B_LOCAL_VALUE_VERSION_PROOF",
        "price_source":"B_LOCAL_PRICE_PROOF_AND_TV_SEPARATE_FEED",
        "cvd_status":"UNKNOWN_NOT_JOINED" if cvd_join is None else cvd_join["status"],
        "tv_cvd_join":cvd_join,"auxiliary_same_decision":aux,
        "ctrader_cvd_status":"UNKNOWN_NOT_JOINED" if aux is None else "SEE_LOCAL_AUXILIARY_COUNTS",
        "sentiment_status":"UNKNOWN_NOT_JOINED" if aux is None else "SEE_LOCAL_AUXILIARY_COUNTS",
        "config_status":"NOT_ATTESTED",
        "cross_feed_price_equivalence_assumed":False,
        "independent_source_proof":False,"predictive_admission":False,
        "edge":"NOT_ESTABLISHED","orders_enabled":False,
        "notifications_enabled":False,"track_b_live_connected":False,
    }
