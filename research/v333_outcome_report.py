"""REMURA V33.3 — local descriptive outcome report, 27/11/2026.
Read-only. No network, no timer, no historical admission or trading advice.
Report limited to captures in last seven calendar days.
"""
import sys,json,time,sqlite3,hashlib,unittest
from decimal import Decimal
from pathlib import Path
from contextlib import closing
BASE=Path.home()/".remura-v296"
HERE=BASE/"v318"
M5=300000
DAY=86400000
HOURS=(1,4,24)
FLAGS=("absorption_candidate","volume_anomaly_2x","price_delta_divergence_30m")
ARMS=("price_only","footprint_only","footprint_plus_cot","footprint_cot_levels","footprint_cot_retail","footprint_cot_levels_retail")
def deps():
    sys.path[:0]=[str(HERE),str(BASE/"v311"),str(BASE/"v312"),str(BASE/"v301"),str(BASE)]
def ro(p):
    db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3)
    db.execute("PRAGMA query_only=ON")
    return db
def verify(raw,h):
    if hashlib.sha256(raw).hexdigest()!=h:raise ValueError("packet_digest")
    return json.loads(raw)
def entry(capture):return (capture//M5+1)*M5
def move(bars,start,end):
    seq=[bars.get(t) for t in range(start,end,M5)]
    if not seq or any(b is None for b in seq):return None
    return (Decimal(seq[-1]["c"])-Decimal(seq[0]["o"]))*10000
def mean(v):
    return str(round(sum(v)/len(v),3)) if v else None
def stats(v):
    return {"n":len(v),"mean_signed_pips":mean(v),"mean_absolute_pips":mean([abs(x) for x in v]),"up":sum(x>0 for x in v),"down":sum(x<0 for x in v)}
def radar_report(packets,bars,now):
    out={}
    for h in HOURS:
        span=h*3600000
        groups={k:{g:[] for g in ("true","false","unavailable")} for k in FLAGS}
        allmoves=[];pending=missing=overdue=excluded=0;next_start=0
        # Common chronological non-overlap selection, independent of flag or outcome.
        for p in packets:
            t=entry(p["capture_ms"]);end=t+span
            if t<next_start:excluded+=1;continue
            next_start=end
            if end>now:pending+=1;continue
            v=move(bars,t,end)
            if v is None:
                missing+=1;overdue+=int(now-end>=2*DAY);continue
            allmoves.append(v)
            for k in FLAGS:
                f=p["features"].get(k)
                groups[k]["true" if f is True else "false" if f is False else "unavailable"].append(v)
        out[str(h)]={"all":stats(allmoves),"pending":pending,"missing":missing,"overdue":overdue,"overlap_excluded":excluded,
            "flags":{k:{g:stats(v) for g,v in a.items()} for k,a in groups.items()}}
    return out
def multi_report(obs,outcomes,now):
    report={}
    for h in HOURS:
        allv={a:[] for a in ARMS};trades={a:0 for a in ARMS}
        non={a:[] for a in ARMS};pending=missing=0;next_start=0
        for ident,t,p in obs:
            end=t+h*3600000
            chosen=t>=next_start
            if chosen:next_start=end
            if end>now:pending+=1;continue
            r=outcomes.get((ident,h))
            if r is None:missing+=1;continue
            net=r["net_pips"]
            if set(net)!=set(ARMS) or set(p["sides"])!=set(ARMS):raise ValueError("arms")
            for a in ARMS:
                x=Decimal(str(net[a]))
                if not x.is_finite():raise ValueError("net")
                allv[a].append(x);trades[a]+=int(p["sides"][a]!=0)
                if chosen:non[a].append(x)
        report[str(h)]={"pending":pending,"missing":missing,"methods":{a:{"n":len(allv[a]),"positions":trades[a],"mean_net_pips":mean(allv[a]),"positive":sum(x>0 for x in allv[a]),"nonoverlap_n":len(non[a]),"nonoverlap_mean_net_pips":mean(non[a])} for a in ARMS}}
    return report
def run():
    from v310_multifeed import tv_bar
    now=time.time_ns()//1000000;lower=now-7*DAY
    packets=[];obs=[];outcomes={}
    with closing(ro(HERE/"radar-v331.sqlite3")) as db:
        for c,t,d,raw in db.execute("SELECT close_ms,capture_ms,digest,packet FROM radar_observations WHERE capture_ms>? AND capture_ms<=? ORDER BY capture_ms,close_ms",(lower,now)):
            p=verify(raw,d)
            if p["schema"]!="remura.v331.radar.local.v1" or p["close_ms"]!=c or p["capture_ms"]!=t or not 0<c<=t or p["prospective_admitted"] is not False:raise ValueError("radar_scope")
            packets.append(p)
    with closing(ro(HERE/"multifactor.sqlite3")) as db:
        for ident,t,raw in db.execute("SELECT id,entry_ms,packet FROM v318_observations WHERE entry_ms>? AND entry_ms<=? ORDER BY entry_ms",(lower,now)):
            p=verify(raw,ident)
            if p["entry_ms"]!=t or not p["frozen_ms"]<t or p["prospective_admitted"] is not False:raise ValueError("multi_scope")
            obs.append((ident,t,p))
        for ident,h,raw in db.execute("SELECT x.id,x.hours,x.result FROM v318_outcomes x JOIN v318_observations o ON o.id=x.id WHERE x.cost=1 AND o.entry_ms>? AND o.entry_ms<=? AND x.asof_ms<=?",(lower,now,now)):
            outcomes[(ident,h)]=json.loads(raw)
    bars={}
    with closing(ro(BASE/"v312/science-tv.sqlite3")) as db:
        for rawmeta,raw,d in db.execute("SELECT metadata,raw,digest FROM events WHERE close_ms>? AND close_ms<=? AND received_ms<=? AND seen_ms<=? ORDER BY close_ms",(lower,now,now,now)):
            b=tv_bar(json.loads(rawmeta),raw,d,now)
            if b["open_ms"] in bars:raise ValueError("duplicate")
            bars[b["open_ms"]]=b
    return {"status":"LOCAL_DESCRIPTIVE_REPORT","window_days":7,"radar_captures":len(packets),"multifactor_started_entries":len(obs),"multifactor_cost_pips":1,"radar":radar_report(packets,bars,now),"multifactor":multi_report(obs,outcomes,now),"persistent_write":False,"prospective_admitted":False}
class Tests(unittest.TestCase):
    def test_move(self):
        self.assertEqual(entry(M5),2*M5)
        self.assertEqual(move({M5:{"o":"1.1000","c":"1.1002"}},M5,2*M5),Decimal(2))
        self.assertIsNone(move({},M5,2*M5))
    def test_radar_overlap(self):
        p=[{"capture_ms":M5,"features":{FLAGS[0]:True}},{"capture_ms":2*M5,"features":{FLAGS[0]:False}}]
        start=2*M5
        bars={t:{"o":"1.1","c":"1.1001"} for t in range(start,start+3600000,M5)}
        r=radar_report(p,bars,start+3600000)["1"]
        self.assertEqual(r["all"]["n"],1);self.assertEqual(r["overlap_excluded"],1)
        self.assertEqual(r["flags"][FLAGS[0]]["true"]["n"],1)
    def test_multi(self):
        obs=[("a",M5,{"sides":{a:0 for a in ARMS}})]
        r=multi_report(obs,{("a",1):{"net_pips":{a:0 for a in ARMS}}},M5+3600000)
        self.assertEqual(r["1"]["methods"][ARMS[0]]["positions"],0)
        self.assertEqual(r["1"]["methods"][ARMS[0]]["n"],1)
        self.assertEqual(r["4"]["pending"],1)
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--report"]:
        deps()
        try:print("V333 REPORT",json.dumps(run(),sort_keys=True))
        except Exception as e:print("V333 REPORT STOP",type(e).__name__);sys.exit(2)
    else:raise SystemExit("--selftest | --report")
