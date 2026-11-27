"""REMURA V31.7 LAB: local as-of source join, no provider calls or ledger writes.
Myfxbook collection time is not verified provider event time. No prediction,
historical backfill of observation timestamps, or admission to Shark Science.
"""
import hashlib,json,math,re,sqlite3,sys,time,unittest
from pathlib import Path
LEVELS=("day1","day2","day3","previous_day","week","current_month","previous_month")
MAX_RETAIL_AGE=3600000
MAX_TV_AGE=600000
def clock():return time.time_ns()//1000000
def number(x):return type(x) in (int,float) and math.isfinite(x)
def retail(p,asof):
    fields={"source","symbol","collection_ms","read_ms","long_pct","short_pct","source_sha256"}
    if type(p) is not dict or set(p)!=fields or p["source"]!="Myfxbook Community Outlook" or p["symbol"]!="EURUSD":raise ValueError("retail_identity")
    c,r=p["collection_ms"],p["read_ms"]
    if any(type(t) is not int for t in (c,r,asof)) or not 0<c<=r<=asof:raise ValueError("retail_clock")
    if not re.fullmatch("[a-f0-9]{64}",p["source_sha256"]):raise ValueError("retail_digest")
    l,s=p["long_pct"],p["short_pct"]
    if not all(number(x) and 0<=x<=100 for x in (l,s)) or abs(l+s-100)>.2:raise ValueError("retail_percent")
    return {"status":"LOCAL_COLLECTION_FRESH_ORIGIN_UNKNOWN" if asof-c<=MAX_RETAIL_AGE else "STALE_LOCAL_COLLECTION",
            "collection_age_sec":(asof-c)//1000,"origin_verified":False,"predictive_admitted":False,
            "long_pct":l,"short_pct":s,"collection_ms":c,"read_ms":r,"source_sha256":p["source_sha256"]}
def levels(snapshot,close_ms,price):
    if type(close_ms) is not int or close_ms<=0 or not number(price) or price<=0:raise ValueError("bar")
    vals=snapshot.get("levels",{});origins=snapshot.get("level_origin_ms",{})
    if type(vals) is not dict or type(origins) is not dict:raise ValueError("level_shape")
    out={}
    for k in LEVELS:
        v,t=vals.get(k),origins.get(k)
        if v is None:status="MISSING_VALUE"
        elif not number(v) or v<=0:status="INVALID_VALUE"
        elif t is None:status="MISSING_ORIGIN"
        elif type(t) is not int or t<=0 or t>close_ms:status="INVALID_ORIGIN"
        elif t>close_ms-300000:status="ORIGIN_WITHIN_BAR"
        else:status="AVAILABLE_DESCRIPTIVE"
        out[k]={"status":status}
        if status=="AVAILABLE_DESCRIPTIVE":
            out[k].update(origin_ms=t,distance_pips=(price-v)*10000)
    return out
def packet(meta,raw,digest,bar,retail_input,asof):
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("tv_digest")
    close=bar["close_ms"]
    if type(close) is not int or not 0<close<=meta["received_at_ms"]<=asof or close!=meta["bar_close_ms"]:raise ValueError("tv_clock")
    snapshot=json.loads(raw)["snapshot"]
    return {"schema":"remura.v317.local.features.v1","asof_ms":asof,"symbol":"EURUSD",
            "tv_sha256":digest,"tv_age_sec":(asof-close)//1000,"tv_fresh":asof-close<=MAX_TV_AGE,
            "levels":levels(snapshot,close,float(bar["c"])),"retail":retail(retail_input,asof),
            "prospective_admitted":False,"participant_identity":None}
def report(input_bytes):
    if not 0<len(input_bytes)<=8192:raise ValueError("input_size")
    b=Path.home()/".remura-v296"
    sys.path[:0]=[str(b/"v311"),str(b/"v312"),str(b/"v301"),str(b)]
    from v310_multifeed import tv_bar
    p=b/"tv-custody.sqlite3"
    db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3)
    try:
        db.execute("PRAGMA query_only=ON")
        row=db.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
            ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) DESC LIMIT 1""").fetchone()
    finally:db.close()
    if row is None:raise ValueError("empty_custody")
    now=clock();m=json.loads(row[0]);bar=tv_bar(m,row[1],row[2],now)
    out=packet(m,row[1],row[2],bar,json.loads(input_bytes),now)
    r=out["retail"]
    # Only diagnostic metadata leaves the process, not private source values.
    return {"tv_age_sec":out["tv_age_sec"],"tv_fresh":out["tv_fresh"],
            "levels":{k:v["status"] for k,v in out["levels"].items()},
            "myfxbook_status":r["status"],"myfxbook_age_sec":r["collection_age_sec"],
            "provider_origin_verified":False,"prospective_admitted":False,"persistent_write":False}
class Tests(unittest.TestCase):
    def test_retail(self):
        p=dict(source="Myfxbook Community Outlook",symbol="EURUSD",collection_ms=1000,read_ms=2000,long_pct=60,short_pct=40,source_sha256="a"*64)
        self.assertEqual(retail(p,3000)["status"],"LOCAL_COLLECTION_FRESH_ORIGIN_UNKNOWN")
        self.assertFalse(retail(p,3000)["predictive_admitted"])
        self.assertEqual(retail(p,MAX_RETAIL_AGE+1001)["status"],"STALE_LOCAL_COLLECTION")
        with self.assertRaises(ValueError):retail(p,1999)
        with self.assertRaises(ValueError):retail(dict(p,long_pct=99),3000)
    def test_levels(self):
        s={"levels":{"week":1.1,"day1":1.2,"day2":1.3,"day3":0},"level_origin_ms":{"week":300000,"day2":850000}}
        r=levels(s,900000,1.101)
        self.assertEqual(r["week"]["status"],"AVAILABLE_DESCRIPTIVE")
        self.assertAlmostEqual(r["week"]["distance_pips"],10)
        self.assertEqual(r["day1"]["status"],"MISSING_ORIGIN")
        self.assertEqual(r["day2"]["status"],"ORIGIN_WITHIN_BAR")
        self.assertEqual(r["day3"]["status"],"INVALID_VALUE")
    def test_packet(self):
        raw=b'{"snapshot":{"levels":{},"level_origin_ms":{}}}'
        d=hashlib.sha256(raw).hexdigest()
        r=dict(source="Myfxbook Community Outlook",symbol="EURUSD",collection_ms=1000,read_ms=2000,long_pct=50,short_pct=50,source_sha256="a"*64)
        out=packet({"bar_close_ms":1000,"received_at_ms":1100},raw,d,{"close_ms":1000,"c":1.1},r,3000)
        self.assertTrue(out["tv_fresh"]);self.assertFalse(out["prospective_admitted"])
        with self.assertRaises(ValueError):packet({"bar_close_ms":1000,"received_at_ms":1100},raw,"b"*64,{"close_ms":1000,"c":1.1},r,3000)
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--report"]:
        try:print(json.dumps(report(sys.stdin.buffer.read(8193)),sort_keys=True))
        except Exception as e:print("V317_STOP",type(e).__name__);sys.exit(2)
    else:raise SystemExit("LAB: --selftest or --report")
