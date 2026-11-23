#!/usr/bin/env python3
"""REMURA V20.6: bounded, aggregate-only, offline comparison of two retail feeds.

Use already-existing local JSON Myfxbook and PRIVATE Capital DEMO; this script
does not fetch them, write databases, use credentials or emit per-market results.
It never claims the populations are interchangeable, or identifies orders by
institutional market participants. Historical first_seen and alpha not proven.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re

SCHEMA="remura.v206.aggregate.retail.two_source_snapshot.v1"
MAX_BYTES=750_000
MAX_GAP_SECONDS=600
SYMBOL_RE=re.compile(r"^[A-Z0-9]{3,12}$")


def _utc(value: object) -> dt.datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError("explicit_utc_z_required")
    try:
        t=dt.datetime.fromisoformat(value[:-1]+"+00:00")
    except ValueError as e:
        raise ValueError("invalid_snapshot_timestamp") from e
    if t.utcoffset()!=dt.timedelta(0):
        raise ValueError("invalid_utc_timezone")
    return t


def _pct(value: object) -> float:
    if type(value) not in (float,int) or not math.isfinite(value) or not 0<=value<=100:
        raise ValueError("invalid_retail_percentage")
    return float(value)


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("file_not_found_or_symlink")
    raw=path.read_bytes()
    if not raw or len(raw)>MAX_BYTES:
        raise ValueError("file_empty_or_oversized")
    try:
        j=json.loads(raw.decode("utf-8"),parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))
    except (UnicodeError,ValueError) as e:
        raise ValueError("invalid_snapshot_json") from e
    if type(j) is not dict:
        raise ValueError("unexpected_snapshot_shape")
    return j


def audit(m: dict,c: dict) -> dict:
    """Deterministic aggregate; no market names, tickers or private values in output."""
    if type(m) is not dict or type(c) is not dict:
        raise ValueError("snapshots_required")
    if (m.get("status")!="ok" or m.get("source")!="Myfxbook Community Outlook"
        or c.get("status")!="ok" or c.get("source")!="Capital.com Client Sentiment"
        or c.get("metric")!="client_positions" or c.get("environment")!="demo"):
        raise ValueError("wrong_feed_identity")
    m_time,c_time=_utc(m.get("updatedAt")),_utc(c.get("updatedAt"))
    gap=abs(round((m_time-c_time).total_seconds()))
    if gap>MAX_GAP_SECONDS:
        raise ValueError("snapshots_not_contemporaneous")
    mx,cp=m.get("symbols"),c.get("symbols")
    if type(mx) is not dict or type(cp) is not dict or not 30<=len(mx)<=120 or not 25<=len(cp)<=40:
        raise ValueError("unsupported_market_counts")
    if any(not SYMBOL_RE.fullmatch(k) for k in set(mx)|set(cp)):
        raise ValueError("unsafe_or_invalid_market_identity")
    both=sorted(set(mx)&set(cp))
    if len(both)<25 or len(both)>34:
        raise ValueError("unbounded_or_insufficient_overlap")
    states={"both_majority_long":0,"both_majority_short":0,
            "myfx_long_capital_short":0,"myfx_short_capital_long":0,
            "neutral_ties":0,"abs_diff_ge_10pp":0,"abs_diff_ge_20pp":0,
            "abs_diff_ge_30pp":0,"abs_diff_ge_40pp":0,
            "same_extreme_ge_70_or_le_30":0,"opposite_extreme_ge_70_le_30":0}
    distances=[]
    for sym in both:
        a,b=mx[sym],cp[sym]
        if type(a) is not dict or type(b) is not dict:
            raise ValueError("bad_market_row")
        a_t,b_t=_utc(a.get("t")),_utc(b.get("t"))
        # Prevent accidental joins of old individual snapshots against new top-level snapshots.
        if a_t!=m_time or b_t!=c_time:
            raise ValueError("misaligned_market_observation")
        ml,ms,cl,cs=(_pct(a.get("lPct")),_pct(a.get("sPct")),
                      _pct(b.get("lPct")),_pct(b.get("sPct")))
        if abs(ml+ms-100)>0.2 or abs(cl+cs-100)>0.2:
            raise ValueError("invalid_long_short_complement")
        if ml>50 and cl>50:
            states["both_majority_long"]+=1
        elif ml<50 and cl<50:
            states["both_majority_short"]+=1
        elif ml>50 and cl<50:
            states["myfx_long_capital_short"]+=1
        elif ml<50 and cl>50:
            states["myfx_short_capital_long"]+=1
        else:
            states["neutral_ties"]+=1
        delta=abs(ml-cl)
        distances.append(delta)
        for pp in (10,20,30,40):
            if delta>=pp:
                states[f"abs_diff_ge_{pp}pp"]+=1
        if ml>=70 and cl>=70 or ml<=30 and cl<=30:
            states["same_extreme_ge_70_or_le_30"]+=1
        if ml>=70 and cl<=30 or ml<=30 and cl>=70:
            states["opposite_extreme_ge_70_le_30"]+=1
    distances.sort()
    n=len(both)
    agree=states["both_majority_long"]+states["both_majority_short"]
    oppose=states["myfx_long_capital_short"]+states["myfx_short_capital_long"]
    median=(distances[(n-1)//2]+distances[n//2])/2
    return {
        "schema":SCHEMA,
        "sources":["Myfxbook Community Outlook public snapshot","Capital.com DEMO private client positions"],
        "myfxbook_observed_at_utc":m["updatedAt"],
        "capital_observed_at_utc":c["updatedAt"],
        "snapshot_gap_seconds":gap,
        "source_market_counts":{"myfxbook":len(mx),"capital_demo":len(cp)},
        "overlap_market_count":n,
        "capital_markets_not_in_public_myfxbook":len(cp)-n,
        "majority_orientation":{"agree":agree,"opposite":oppose,"neutral":states["neutral_ties"]},
        "bucket_counts":states,
        "mean_absolute_long_percentage_point_difference":round(sum(distances)/n,2),
        "median_absolute_long_percentage_point_difference":round(median,2),
        "provider_populations_and_denominators_equivalent":False,
        "prices_or_future_outcomes_available":False,
        "institutional_positioning_attested":False,
        "directional_alpha_established":False,
        "eligible_as_per_trade_first_seen":False,
        "per_market_values_or_names_exported":False,
        "cloudflare_calls":0,
        "provider_calls":0,
        "orders_enabled":False,
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--myfxbook-latest",type=Path,required=True)
    ap.add_argument("--private-capital-latest",type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(audit(_read(args.myfxbook_latest),_read(args.private_capital_latest)),
                     indent=2,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
