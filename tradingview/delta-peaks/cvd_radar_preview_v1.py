#!/usr/bin/env python3
# REMURA v0.8.68 LAB — 14/11/2026 16:46 CET
"""Explainable CVD radar, no weights, no signals, no inferred institutional trades.
Input must be validated dedicated FX:EURUSD envelopes. Observed and hypothesized
facts stay separate; missing/zero are distinct. Never label ER as trade direction.
"""
from collections import Counter
from math import isfinite
from datetime import datetime, timezone
from cvd_telemetry_preview_v1 import validate,SYMBOL
from volume_features_v1 import sign
from volume_quality_v1 import diagnose

def relation(a,b):
    if a is None or b is None:
        return "UNKNOWN"
    if a==0 or b==0:
        return "NEUTRAL"
    return "ALIGNED" if a==b else "DISAGREE"

def describe(e,*,received_ms,as_of_ms):
    v=validate(e,received_ms=received_ms)
    if type(as_of_ms) is not int or max(received_ms,v["bar_close_ms"])>as_of_ms:
        raise ValueError("not_available_as_of")
    p,c=e["snapshot"],e["cvd"]
    o,fp,ev=p["ohlc"],p["footprint"],p["events"]
    t=p["bar_close_ms"]
    atr=o["atr14"] if o["atr14"] and o["atr14"]>0 else None
    ds=sign(p["delta_intrabar"])
    fs=sign(fp["delta"]) if fp["available"] else None
    ps=sign(o["close"]-o["open"])
    cs=sign(c["trusted_delta"])
    checks=diagnose(p)
    blocked="REVIEW" in checks.values()
    dual=c["price_bull"] and c["price_bear"]
    candidate=("AMBIGUOUS" if dual else "BULL" if c["price_bull"] else
               "BEAR" if c["price_bear"] else "NONE")
    selected=(None if candidate in ("NONE","AMBIGUOUS") else
              c["cvd_bull"] if candidate=="BULL" else c["cvd_bear"])
    er=("POSITIVE_EFFORT" if ev["er_positive"] else
        "NEGATIVE_EFFORT" if ev["er_negative"] else "NONE")
    levels=[]
    for key,price in p["levels"].items():
        if price is None:
            continue
        origin=p["level_origin_ms"][key]
        prior=origin<=p["bar_open_ms"]
        distance=(o["close"]-price)/atr if atr else None
        if distance is not None and not isfinite(distance):
            raise ValueError("nonfinite_distance")
        touches=o["low"]<=price<=o["high"] if prior else None
        levels.append({"name":key,"known_at_bar_open":prior,
                       "distance_close_atr":distance if prior else None,
                       "range_touch":touches,
                       "close_side":sign(o["close"]-price) if touches else None,
                       "sender_retest":ev.get("retest_"+key)})
    hypotheses=[]
    if not blocked and not dual:
        if er=="POSITIVE_EFFORT":
            hypotheses.append("POSSIBLE_BUYING_EFFORT_ABSORPTION")
        elif er=="NEGATIVE_EFFORT":
            hypotheses.append("POSSIBLE_SELLING_EFFORT_ABSORPTION")
        if selected is True:
            hypotheses.append("CVD_DIVERGENCE_FILTER_SELECTED")
    return {"schema":"remura.tv.cvd.radar.preview.v1","version":"0.8.68-lab",
            "status":"BLOCKED_REVIEW" if blocked else "AMBIGUOUS" if dual else "OBSERVATION_ONLY",
            "symbol":SYMBOL,"bar_close_ms":t,"available_at_ms":max(t,received_ms),
            "candidate":candidate,"cvd_selected":selected,
            "observed":{"er":er,"cvd_eligible":c["eligible"],"cvd_continuous":c["continuous"],
                        "delta_footprint_relation":relation(ds,fs),
                        "delta_price_body_relation":relation(ds,ps),
                        "cvd_delta_relation":relation(cs,ds),
                        "footprint_available":fp["available"],
                        "imbalance_count_relation":relation(
                            sign(fp["imb_buy_rows"]-fp["imb_sell_rows"]) if fp["available"] and
                            fp["imb_buy_rows"] is not None and fp["imb_sell_rows"] is not None else None,ds),
                        "range_atr":(o["high"]-o["low"])/atr if atr else None,
                        "utc_hour":datetime.fromtimestamp(t/1000,timezone.utc).hour,
                        "levels":levels},
            "diagnostics":checks,"hypotheses":hypotheses,
            "verdict":"NO_OPERATIONAL_SIGNAL","scientific_admission":False,
            "orders_enabled":False,"notifications_enabled":False}

def aggregate_radar(valid,*,as_of_ms):
    counts=Counter(); cooccurrence=Counter()
    for row,e,v in valid:
        r=describe(e,received_ms=row["received_at_ms"],as_of_ms=as_of_ms)
        if (r["bar_close_ms"]!=row["bar_close_ms"] or v["event_key"]!=row["event_key"]):
            raise ValueError("radar_identity")
        counts[r["status"]]+=1
        if r["status"]!="OBSERVATION_ONLY":
            continue
        o=r["observed"]
        counts["FP_"+o["delta_footprint_relation"]]+=1
        counts["ER_"+o["er"]]+=1
        if r["candidate"]!="NONE":
            group="CVD_SELECTED" if r["cvd_selected"] else "PRICE_ONLY"
            cooccurrence[group+"|"+o["er"]+"|FP_"+o["delta_footprint_relation"]]+=1
    return {"schema":"remura.tv.cvd.radar.aggregate.preview.v1","counts":dict(counts),
            "candidate_cooccurrences":dict(cooccurrence),"verdict":"NO_OPERATIONAL_SIGNAL",
            "scientific_admission":False,"orders_enabled":False,"notifications_enabled":False}
