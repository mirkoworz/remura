#!/usr/bin/env python3
# REMURA v0.8.59 LAB — 14/11/2026 12:45 CET
"""Offline CVD + original delta snapshot contract.
New FX:EURUSD cohort, never relabel as FXCM:EURUSD. No live ingestion.
Strict v1 compatibility validation uses an internal copy only; no old event key.
Configuration, source quality and flags are sender declarations, no proof of edge.
"""
from hashlib import sha256
import json
import math
from fx_pilot_config_v1 import REFERENCE
from validate_telemetry_v1 import validate_payload,MAX_BYTES

SCHEMA="remura.tv.flow.cvd.preview.v1"
SNAPSHOT_SCHEMA="remura.tv.flow.cvd.snapshot.preview.v1"
VERSION="0.9.1-cvd-lab"
SYMBOL="FX:EURUSD"
M5=300000
CONFIG={**REFERENCE,"symbol":SYMBOL,"indicator_version":VERSION,
        "cvd_left":2,"cvd_right":2,"cvd_min_distance":3,"cvd_max_distance":72,
        "cvd_warmup":12,"cvd_min_price_ticks":5,"cvd_min_difference":10.0}
FIELDS={"model","intrabar_count","complete","continuous","day_valid","segment_id",
        "segment_bars","day_key_ms","raw_delta","trusted_delta","daily_cvd",
        "segment_cvd","eligible","price_bull","price_bear","cvd_bull","cvd_bear","pivot_close_ms"}

def require(ok,reason):
    if not ok:
        raise ValueError(reason)

def config_id(c):
    require(type(c) is dict and set(c)==set(CONFIG),"config_fields")
    normalized={}
    for k,expected in CONFIG.items():
        v=c[k]
        if type(expected) is float:
            require(type(v) in (int,float) and math.isfinite(v),"config_numeric")
            v=float(v)
        else:
            require(type(v) is type(expected),"config_type")
        require(v==expected,"config_not_frozen")
        normalized[k]=v
    return sha256(json.dumps({"schema":SCHEMA,"configuration":normalized},sort_keys=True,
                             separators=(",",":"),allow_nan=False).encode()).hexdigest()

def validate(envelope,*,received_ms):
    require(type(received_ms) is int,"receiver_timestamp_required")
    require(type(envelope) is dict and set(envelope)=={"schema","snapshot","configuration","cvd"},"envelope_fields")
    require(envelope["schema"]==SCHEMA,"envelope_schema")
    require(len(json.dumps(envelope,separators=(",",":"),allow_nan=False).encode())<=MAX_BYTES,"envelope_size")
    p=envelope["snapshot"]
    require(type(p) is dict and p.get("schema")==SNAPSHOT_SCHEMA and p.get("version")==VERSION,"snapshot_version")
    require(p.get("symbol")==SYMBOL and p.get("feed")=="FX" and p.get("timeframe")=="5","wrong_feed")
    # Compatibility view ONLY. Validate shared fields with the old strict validator.
    check=validate_payload(dict(p,schema="remura.tv.flow.v1",version="0.8.1-lab"),
                           received_ms=received_ms,expected_symbol=SYMBOL)
    require(check["timely_for_prospective"],"not_timely")
    t=p["bar_close_ms"]
    require(t%M5==0 and t-p["bar_open_ms"]==M5,"not_full_m5")
    require(all(x is None or x<=t for x in p["level_origin_ms"].values()),"future_level")
    fingerprint=config_id(envelope["configuration"])
    require(p["quality"]["lower_tf"]==CONFIG["lower_tf"] and p["quality"]["daily_anchor"]==CONFIG["daily_anchor"],"config_snapshot_mismatch")
    c=envelope["cvd"]
    require(type(c) is dict and set(c)==FIELDS and c["model"]=="D08_SEGMENT_PORT_V091","cvd_shape")
    for k in ("complete","day_valid","eligible","price_bull","price_bear","cvd_bull","cvd_bear"):
        require(type(c[k]) is bool,"cvd_flag_type")
    require(c["continuous"] is None or type(c["continuous"]) is bool,"cvd_continuity_type")
    for k in ("intrabar_count","segment_id","segment_bars","day_key_ms"):
        require(type(c[k]) is int and c[k]>=0,"cvd_counter_type")
    require(c["intrabar_count"]<=5 and c["day_key_ms"]>1_000_000_000_000 and c["day_key_ms"]<=p["bar_open_ms"],"cvd_counter_scope")
    for k in ("raw_delta","trusted_delta","daily_cvd","segment_cvd"):
        v=c[k]
        require(v is None or type(v) in (int,float) and math.isfinite(v),"cvd_number")
    require((c["raw_delta"] is not None)==c["complete"],"raw_delta_availability")
    require((c["continuous"] is not None)==c["complete"],"continuity_availability")
    require((c["trusted_delta"] is not None)==(c["continuous"] is True),"trusted_delta_availability")
    require((c["daily_cvd"] is not None)==c["day_valid"],"daily_availability")
    require((c["segment_cvd"] is not None)==(c["segment_bars"]>=2),"segment_availability")
    if c["complete"]:
        require(c["intrabar_count"]==5 and c["segment_id"]>=1 and c["segment_bars"]>=1,"complete_cvd_scope")
        require((c["segment_bars"]>=2)==c["continuous"],"segment_continuity")
        if c["continuous"]:
            require(c["raw_delta"]==c["trusted_delta"],"trusted_delta_mismatch")
        if c["day_valid"] and not c["continuous"]:
            require(c["day_key_ms"]==p["bar_open_ms"],"daily_gap")
    else:
        require(c["segment_bars"]==0 and not c["day_valid"],"incomplete_cvd_scope")
    require(c["eligible"]==(c["continuous"] is True and c["segment_bars"]>=CONFIG["cvd_warmup"]),"eligibility")
    require(not(c["price_bull"] or c["price_bear"]) or c["eligible"],"pivot_without_warmup")
    require((not c["cvd_bull"] or c["price_bull"]) and (not c["cvd_bear"] or c["price_bear"]),"cvd_not_subset")
    if c["price_bull"] or c["price_bear"]:
        require(type(c["pivot_close_ms"]) is int and c["pivot_close_ms"]==t-CONFIG["cvd_right"]*M5,"pivot_confirmation_clock")
    else:
        require(c["pivot_close_ms"] is None,"unexpected_pivot")
    delta_difference=None
    if c["trusted_delta"] is not None and p["delta_intrabar"] is not None:
        delta_difference=c["trusted_delta"]-p["delta_intrabar"]
        require(math.isfinite(delta_difference),"delta_difference_nonfinite")
    return {"schema":SCHEMA,"status":"DESCRIPTIVE_PREVIEW_ONLY",
            "event_key":"|".join((SYMBOL,"5",str(t),VERSION)),
            "declared_config_sha256":fingerprint,"received_at_ms":received_ms,
            "bar_close_ms":t,"lag_ms":check["lag_ms"],"cvd_complete":c["complete"],
            "cvd_continuous":c["continuous"],"delta_difference":delta_difference,
            "source_cohort":"FX_EURUSD_CVD_D08_PORT_V091",
            "effective_inputs_attested":False,"institutional_admissible":False,
            "predictive_admissible":False,"orders_enabled":False,"notifications_enabled":False}
