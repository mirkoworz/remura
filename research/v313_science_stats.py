"""V31.3 LAB: read-only matched benchmark statistics, no certification or trading.
Greedy non-overlap per horizon/cost; does not imply independence across samples.
"""
import sqlite3,json,hashlib,unittest
from decimal import Decimal
from pathlib import Path
ARMS=("price_only","footprint_only","footprint_plus_cot")
def paired(rows,hours,cost):
    if hours not in (1,4,24) or cost not in (0,1,2):raise ValueError("scope")
    sums={a:Decimal(0) for a in ARMS}; wins={a:0 for a in ARMS}
    last=-1;n=0;excluded=0;ids=set()
    for identity,entry,end,net in sorted(rows,key=lambda r:(r[1],r[0])):
        if identity in ids or end-entry!=hours*3600000 or set(net)!=set(ARMS):raise ValueError("outcome")
        ids.add(identity)
        vals={a:Decimal(str(net[a])) for a in ARMS}
        if not all(x.is_finite() for x in vals.values()):raise ValueError("numeric")
        if entry<last:
            excluded+=1;continue
        n+=1;last=end
        for a in ARMS:
            sums[a]+=vals[a]
            wins[a]+=vals[a]>0
    return {"hours":hours,"cost_pips":cost,"matched_nonoverlap":n,"excluded_overlap":excluded,
        "mean_net_pips":{a:str(sums[a]/n) if n else None for a in ARMS},
        "mean_increment_vs_price":{a:str((sums[a]-sums["price_only"])/n) if n else None for a in ARMS[1:]},
        "positive_net_count":wins,"prospective_admitted":False,"inferential_claim":False}
def report(db):
    out=[]
    for h in (1,4,24):
        missing=db.execute("SELECT COUNT(*) FROM terminal_missing WHERE hours=?",(h,)).fetchone()[0]
        for cost in (0,1,2):
            rows=[]
            for identity,packet,blob,asof in db.execute("SELECT x.id,o.packet,x.result,x.asof_ms FROM outcomes x JOIN observations o ON o.id=x.id WHERE x.hours=? AND x.cost=?",(h,cost)):
                if hashlib.sha256(packet).hexdigest()!=identity:raise ValueError("packet")
                p=json.loads(packet);r=json.loads(blob)
                if p.get("prospective_admitted") is not False or r.get("prospective_admitted") is not False or r.get("status")!="RETROSPECTIVE_ONLY" or p.get("entry_ms")!=r["entry_ms"] or r["end_ms"]>asof or p.get("price_source")!=r.get("price_source"):raise ValueError("evidence_scope")
                rows.append((identity,r["entry_ms"],r["end_ms"],r["net_pips"]))
            out.append(dict(paired(rows,h,cost),terminal_missing=missing,matched_all=len(rows)))
    return {"local_observations":db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],"groups":out,"certified_observations":0,"status":"LOCAL_UNWITNESSED_ONLY"}
def read_report(path):
    path=Path(path).resolve(strict=True)
    with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=3) as db:
        db.execute("PRAGMA query_only=ON");db.execute("BEGIN")
        return report(db)
class Tests(unittest.TestCase):
    def test_pair(self):
        h=3600000;net=dict(price_only="1",footprint_only="3",footprint_plus_cot="2")
        r=paired([("a",0,h,net),("b",1,h+1,net),("c",h,2*h,net)],1,1)
        self.assertEqual(r["matched_nonoverlap"],2)
        self.assertEqual(r["excluded_overlap"],1)
        self.assertEqual(r["mean_increment_vs_price"]["footprint_only"],"2")
    def test_empty(self):
        self.assertIsNone(paired([],4,2)["mean_net_pips"]["price_only"])
if __name__=="__main__":
    import sys
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif len(sys.argv)==3 and sys.argv[1]=="--report":print(json.dumps(read_report(sys.argv[2]),sort_keys=True))
    else:raise SystemExit("LAB: --selftest or --report path")
