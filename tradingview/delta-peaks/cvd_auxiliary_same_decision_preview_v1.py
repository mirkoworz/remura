#!/usr/bin/env python3
# REMURA v0.8.74 LAB — 14/11/2026 17:06 CET
"""Narrow exact-document cTrader and original retail pin association.
Use original B local audited pairs, no aggregate-to-individual inference.
Earlier prefix-only cTrader is UNKNOWN here, not a negative class.
Only isolated immutable caller snapshots, no production imports/network.
Retail reconciler takes a lab filesystem lock; never point at live storage.
"""
from collections import Counter,defaultdict
from datetime import timedelta
import sqlite3
from fx_m15_decision_preview_v1 import utc,ms
from cvd_squalincome_asof_preview_v1 import index_rows,at_decision
MAX_PAIRS=20 # bound costly per-decision retail shard verification
MAX_EVENTS=1000

def exact_events(db,*,earliest,cutoff,secret):
    from scripts import shark_cvd_source_lineage as source
    source._mac(secret,"0"*64)
    if not source._has_protected_schema(db):
        return None
    triggers={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='research_cvd_observations'")}
    if not {"research_cvd_no_update","research_cvd_no_delete"}.issubset(triggers):
        raise ValueError("private_event_immutability_missing")
    rows=db.execute("SELECT key,symbol,side,confirmed_at,detected_at FROM research_cvd_observations "
        "WHERE symbol='EURUSD' AND substr(detected_at,1,19)>=? AND substr(detected_at,1,19)<=? "
        "ORDER BY detected_at,key LIMIT ?",(earliest.strftime("%Y-%m-%dT%H:%M:%S"),
        cutoff.strftime("%Y-%m-%dT%H:%M:%S"),MAX_EVENTS+1)).fetchall()
    if len(rows)>MAX_EVENTS:
        raise ValueError("exact_event_cap")
    return [r for r in rows if earliest<=utc(r[4])<=cutoff]

def exact_direction(db,events,pair,*,as_of_utc,secret):
    from scripts import shark_cvd_source_lineage as source
    if events is None:
        return "UNKNOWN"
    sym,week,closed,observed,sha,side=pair
    obs=utc(observed); close=utc(closed); directions=set()
    for key,market,orientation,confirmed,detected in events:
        if orientation not in ("bullish","bearish"):
            raise ValueError("invalid_ct_direction")
        if market!=sym or utc(confirmed)>close or not obs-timedelta(minutes=90)<=utc(detected)<=obs:
            continue
        r=source.match(db,event_key=key,original_price_sha=sha,observed_at=observed,as_of=as_of_utc,secret=secret)
        if r["state"]=="EXACT_LOCAL_SOURCE_AND_CHRONOLOGY":
            directions.add("ALIGNED" if (orientation=="bullish")== (side==1) else "OPPOSED")
    return "UNKNOWN" if not directions else "MIXED" if len(directions)>1 else next(iter(directions))

def retail_pin(core,root,pair,*,cutoff,authorized_at):
    from scripts import shark_retail_crossdb_predecision as pin
    from scripts import shark_signal_ingest_decision_link as link
    sym,week,closed,obs,sha,side=pair
    try:
        rows=core.execute("SELECT h.id,p.pinned_at,l.linked_at_utc FROM squalincome_history h "
            f"JOIN {pin.TABLE} p ON p.history_id=h.id JOIN {link.TABLE} l ON l.history_id=h.id "
            "WHERE h.symbol=? AND h.report_date=? AND h.price_time=? AND h.observed_at=? AND h.cot_side=? "
            "AND p.symbol=h.symbol AND p.observed_at=h.observed_at AND l.merged_document_sha256=? LIMIT 2",
            (sym,week,closed,obs,side,sha)).fetchall()
        triggers={r[0] for r in core.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",(pin.TABLE,))}
        if not {"research_predecision_retail_pin_no_update","research_predecision_retail_pin_no_delete"}.issubset(triggers):
            return "UNKNOWN"
        if len(rows)!=1 or any(utc(x)>cutoff for x in rows[0][1:]):
            return "UNKNOWN"
        r=pin.reconcile(core,root,history_id=rows[0][0],authorized_at=authorized_at)
        if r.get("schema")==pin.SCHEMA and r.get("verifiedOriginalRetailPin") is True and r.get("retailActuallyUsedBySqualincome") is False:
            return "LOCAL_ORIGINAL_PIN_VERIFIED"
    except (ValueError,TypeError,sqlite3.Error,OSError):
        pass
    return "UNKNOWN"

def audit(core,private,cvd_rows,*,as_of_utc,days=1,secret=None,retail_root=None,authorized_at=None):
    from scripts import shark_causal_pair_audit as b
    for db in ([core] if private is None else [core,private]):
        if not isinstance(db,sqlite3.Connection) or db.in_transaction or db.execute("PRAGMA query_only").fetchone()[0]!=1:
            raise ValueError("isolated_query_only_snapshot_required")
    if core is private or (retail_root is None)!=(authorized_at is None):
        raise ValueError("auxiliary_scope")
    if type(days) is not int or not 1<=days<=7:
        raise ValueError("auxiliary_days")
    cutoff=utc(as_of_utc); groups=index_rows(cvd_rows)
    pairs=[]
    report=b.audit(core,as_of=as_of_utc,days=days,_verified_pairs=pairs)
    n=report["locallyJoinedCausalPairs"]
    if n is None and pairs or n is not None and n!=len(pairs):
        raise ValueError("pair_scope")
    fx=[p for p in pairs if p[0]=="EURUSD"]
    if len(fx)>MAX_PAIRS:
        raise ValueError("auxiliary_pair_cap")
    identities={(p[0],p[1],utc(p[2]),utc(p[3])) for p in fx}
    if len(identities)!=len(fx):
        raise ValueError("duplicate_auxiliary_pair")
    events=None if private is None else exact_events(private,earliest=cutoff-timedelta(days=days,minutes=90),cutoff=cutoff,secret=secret)
    counts=Counter(); matrix=Counter()
    for pair in fx:
        _,_,closed,obs,_,side=pair
        t,decision=ms(utc(closed)),ms(utc(obs))
        if t%(3*300000) or not t<=decision<=t+180000:
            tv="B_CLOCK_OUTSIDE_TV_HANDOFF"; radar=None
        else:
            tv,radar=at_decision(groups,close_ms=t,decision_ms=decision)
        tv_dir=("UNKNOWN" if radar is None or radar["cvd_selected"] is not True else
                "ALIGNED" if (radar["candidate"]=="BULL")== (side==1) else "OPPOSED")
        ct="UNKNOWN" if private is None else exact_direction(private,events,pair,as_of_utc=as_of_utc,secret=secret)
        retail="UNKNOWN" if retail_root is None else retail_pin(core,retail_root,pair,cutoff=cutoff,authorized_at=authorized_at)
        counts["TV_"+tv]+=1
        counts["CT_EXACT_"+ct]+=1
        counts["RETAIL_"+retail]+=1
        if radar is not None and ct!="UNKNOWN":
            counts["TV_AND_CT_EXACT_LOCAL_SAME_B_DECISION"]+=1
        if radar is not None and ct!="UNKNOWN" and retail=="LOCAL_ORIGINAL_PIN_VERIFIED":
            counts["ALL_LOCAL_PROOF_TYPES_SAME_B_DECISION"]+=1
        matrix["TV_"+tv_dir+"|CT_"+ct+"|RETAIL_"+retail]+=1
    if sum(matrix.values())!=len(fx):
        raise ValueError("matrix_denominator")
    return {"schema":"remura.tv.auxiliary.same.decision.preview.v1","version":"0.8.74-lab",
            "status":"LOCAL_ASSOCIATIONS_ONLY" if n is not None else "B_PROOFS_UNAVAILABLE",
            "b_local_pairs":n,"eurusd_pairs":len(fx) if n is not None else None,
            "counts":dict(sorted(counts.items())),"matrix":dict(sorted(matrix.items())),
            "ct_method":"CLV_TIMES_TICK_VOLUME_PROXY_EXACT_DOCUMENT_ONLY",
            "retail_direction_used":False,"earlier_ct_prefix_tier_included":False,
            "missing_is_negative":False,"cross_database_atomic":False,"independent_provenance":False,
            "retail_actually_used_by_original_signal":False,"scientific_admission":False,
            "orders_enabled":False,"notifications_enabled":False,"edge":"NOT_ESTABLISHED"}
