# REMURA Contributors v0.36 LAB — 16/11/2026 16:27 CET
"""Future Pine wire contract rehearsal. Synthetic only, no sender authentication."""
from hashlib import sha256
import json
from datetime import datetime, timezone, timedelta
from explicit_level_contract_lab_v1 import (INSTRUMENT, METHOD, POLICY, SCHEMA,
    anchor, evaluate, need)
from ledger_v1 import _time

WIRE = "remura.tv.level.explicit.synthetic.v1"
COHORT = "LABFX_EXPLICIT_SYNTHETIC_V1"
CONFIG = {"instrument":list(INSTRUMENT),"symbol":"LABFX:EURUSD",
    "timeframe":"5","method":METHOD,"period_policy":POLICY,
    "effort_result_method":"SYNTHETIC_ER_CONTEXT_ONLY_V1",
    "price_encoding":"DECIMAL_STRING","revision":"FIXTURE_V1"}
CONFIG_ID = sha256(json.dumps(CONFIG,sort_keys=True,separators=(",",":")).encode()).hexdigest()
FIELDS = {"schema","cohort","symbol","timeframe","market","provider","ticker",
    "product","contract","method","period_policy","effort_result_method",
    "config_id","id","period","kind","price","anchor_ms","observed_ms","bar_close_ms"}
EPOCH = datetime(1970,1,1,tzinfo=timezone.utc)

def clock(ms):
    need(type(ms) is int and 0 <= ms < 4102444800000 and ms % 1000 == 0)
    return EPOCH+timedelta(milliseconds=ms)

def utc(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def decode_wire(payload, *, received_ms, synthetic=False):
    need(synthetic is True and type(payload) is dict and set(payload)==FIELDS)
    expected = dict(zip(("market","provider","ticker","product","contract"),INSTRUMENT))
    expected.update(schema=WIRE,cohort=COHORT,symbol=CONFIG["symbol"],timeframe="5",
        method=METHOD,period_policy=POLICY,effort_result_method=CONFIG["effort_result_method"],
        config_id=CONFIG_ID,kind="DELTA_PEAK")
    need(all(payload[k]==v for k,v in expected.items()))
    obs,close,receipt,period_start = (clock(x) for x in
        (payload["observed_ms"],payload["bar_close_ms"],received_ms,payload["anchor_ms"]))
    need(payload["bar_close_ms"]%300000==0 and obs<=close<=receipt)
    need(type(payload["price"]) is str and len(payload["price"])<=32)
    need(period_start==anchor(payload["period"],utc(obs)))
    out={k:payload[k] for k in ("market","provider","ticker","product","contract",
         "id","period","kind","price")}
    out.update(schema=SCHEMA,anchor_utc=utc(period_start),observed_utc=utc(obs),
        available_utc=utc(receipt),metadata={"method":METHOD,"period_policy":POLICY,
        "known_utc":utc(receipt)})
    return out

def handoff(manual, envelopes, *, asof_utc, synthetic=False):
    """Receipt clock is supplied separately; never trust sender availability claims.
    Fixture config identity is required on both sides. Not attestation.
    """
    need(synthetic is True and type(manual) is list and type(envelopes) is list
         and len(manual)<=200 and len(envelopes)<=20)
    _time(asof_utc)
    rows=[]
    for m in manual:
        need(type(m) is dict and set(m)=={"entry","metadata","config_id"})
        need(m["config_id"]==CONFIG_ID)
        rows.append({"entry":m["entry"],"metadata":m["metadata"]})
    automatic=[]
    for item in envelopes:
        need(type(item) is dict and set(item)=={"payload","received_ms"})
        automatic.append(decode_wire(item["payload"],received_ms=item["received_ms"],synthetic=True))
    out=evaluate(rows,automatic,asof_utc=asof_utc,synthetic=True)
    return dict(out,wire_schema=WIRE,config_id=CONFIG_ID,origin="SYNTHETIC",
        config_attested=False,receipt_authenticated=False)
