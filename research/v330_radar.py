"""REMURA V33.0 — 27/11/2026 Europe/Rome.
Read-only EURUSD radar on local confirmed M5 footprints, not exchange flow.
No network, persistence, participant attribution or predictive admission.
"""
import sys,json,time,sqlite3,unittest
from pathlib import Path
from decimal import Decimal
from statistics import median
from contextlib import closing
BASE=Path.home()/".remura-v296"
M5=300000
def deps():
    sys.path[:0]=[str(BASE/"v318"),str(BASE/"v311"),str(BASE/"v312"),str(BASE/"v301"),str(BASE)]
def radar(rows,asof,absorption):
    out={"status":"DESCRIPTIVE_ONLY","source":"TV_FOOTPRINT_CLASSIFIED_FX_EURUSD_M5",
         "participant_identity":None,"prospective_admitted":False,
         "liquidity_order_book":"UNAVAILABLE","futures_lead_lag":"NO_CONNECTED_FUTURES_FEED"}
    if not rows or asof-rows[-1]["close_ms"]>2*M5:
        return {**out,"status":"WAIT_TV_FRESH"}
    last=rows[-1]
    # Contiguous, same configuration and UTC segment, no forward rows.
    seg=[r for r in rows[-min(last["segment_bars"],25):]]
    if any(y["close_ms"]-x["close_ms"]!=M5 for x,y in zip(seg,seg[1:])):
        raise ValueError("segment_gap")
    if any(not 0<r["close_ms"]<=asof for r in seg):raise ValueError("asof")
    if last["volume"]>0:
        out["absorption_candidate"]=absorption(float(last["o"]),float(last["c"]),float(last["delta"]),float(last["volume"]))["candidate"]
    else:out["absorption_candidate"]=None
    prev=seg[:-1]
    base=median(r["volume"] for r in prev) if len(prev)==24 else None
    out["volume_anomaly_2x"]=None if not base else last["volume"]>=2*base
    out["baseline_bars"]=len(prev)
    w=seg[-6:]
    out["price_delta_divergence_30m"]=None
    if len(w)==6:
        move=w[-1]["c"]-w[0]["o"]
        delta=sum(r["delta"] for r in w)
        out["price_delta_divergence_30m"]=(move*delta<0)
    out["latest_age_sec"]=(asof-last["close_ms"])//1000
    out["segment_bars"]=last["segment_bars"]
    out["source_sha256"]=last["digest"]
    return out
def preview():
    from v311_science import records
    from v310_multifeed import tv_bar
    from v294_footprint_cvd import derive
    from v313_intelligence import absorption
    now=time.time_ns()//1000000
    p=BASE/"v312/science-tv.sqlite3"
    with closing(sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3)) as db:
        db.execute("PRAGMA query_only=ON")
        src=records(db,now,now-86400000)
    if not src:return {"status":"WAIT_TV","prospective_admitted":False}
    d=derive([{"metadata":a,"original":b,"sha256":c} for a,b,c in src],now)
    by={x["bar_close_ms"]:x for x in d}
    if src[-1][0]["bar_close_ms"] not in by:return {"status":"WAIT_LATEST_FOOTPRINT","prospective_admitted":False}
    rows=[]
    for a,b,h in src:
        c=a["bar_close_ms"]
        if c not in by:continue
        bar=tv_bar(a,b,h,now)
        f=json.loads(b,parse_float=Decimal)["snapshot"]["footprint"]
        rows.append({**bar,"delta":Decimal(f["delta"]),"volume":Decimal(f["buy"])+Decimal(f["sell"]),
                     "segment_bars":by[c]["segment_bars"],"digest":h})
    return {**radar(rows,now,absorption),"persistent_write":False}
class Tests(unittest.TestCase):
    def row(self,i,volume=10,delta=2):
        return dict(close_ms=(i+1)*M5,segment_bars=i+1,volume=Decimal(volume),delta=Decimal(delta),o=Decimal("1.1"),c=Decimal("1.09999"),digest="a"*64)
    def test_real_feature_shape(self):
        r=[self.row(i) for i in range(24)]+[self.row(24,30,25)]
        o=radar(r,25*M5,lambda *x:{"candidate":True})
        self.assertTrue(o["volume_anomaly_2x"]);self.assertTrue(o["price_delta_divergence_30m"])
        self.assertEqual(o["baseline_bars"],24);self.assertFalse(o["prospective_admitted"])
    def test_missing_and_gap(self):
        r=[self.row(i) for i in range(6)]
        self.assertIsNone(radar(r,6*M5,lambda *x:{"candidate":False})["volume_anomaly_2x"])
        self.assertEqual(radar(r,9*M5,None)["status"],"WAIT_TV_FRESH")
        with self.assertRaises(ValueError):radar(r[:2]+r[3:],6*M5,None)
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--preview"]:
        deps()
        try:print("V330 RADAR",json.dumps(preview(),sort_keys=True))
        except Exception as e:print("V330 RADAR STOP",type(e).__name__);sys.exit(2)
    else:raise SystemExit("--selftest | --preview")
