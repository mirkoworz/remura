"""V31.3 LAB: as-of feature admission and descriptive absorption/lead-lag.
No inference of participant identity, no predictive admission, no network.
"""
import math,unittest
SLOT=300000
MAX_AGE={"TV_PRICE":600000,"CTRADER_PRICE":600000,"FOOTPRINT_DERIVED":600000,"LEVELS":86400000,"COT":14*86400000,"MYFXBOOK":3600000,"CONTRIBUTOR_LEVELS":86400000}
def admit(items,asof):
    result={}
    for source in MAX_AGE:
        p=items.get(source)
        if p is None:result[source]="MISSING";continue
        t=p.get("event_ms");s=p.get("seen_ms")
        if type(t) is not int or type(s) is not int or not 0<t<=s<=asof:
            result[source]="CLOCK_OR_LOOKAHEAD";continue
        if p.get("source_time_verified") is not True:result[source]="ORIGIN_TIME_UNKNOWN";continue
        result[source]="AVAILABLE_DESCRIPTIVE" if asof-t<=MAX_AGE[source] else "STALE"
    return result
def absorption(open_price,close_price,delta,volume,max_move_pips=1,min_imbalance=.5):
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (open_price,close_price,delta,volume,max_move_pips,min_imbalance)) or min(open_price,close_price,volume)<=0 or abs(delta)>volume or max_move_pips<0 or not 0<min_imbalance<=1:raise ValueError("numeric")
    move=(close_price-open_price)*10000
    return {"candidate":abs(move)<=max_move_pips and abs(delta/volume)>=min_imbalance,
            "price_move_pips":move,"delta_fraction":delta/volume,"status":"DESCRIPTIVE_ONLY","participant_identity":None}
def lead_lag(rows,asof):
    # Each row contains synchronized returns with a verified availability time.
    if len(rows)>288:raise ValueError("capacity")
    if any(type(r["close_ms"]) is not int or type(r["seen_ms"]) is not int or not 0<r["close_ms"]<=r["seen_ms"]<=asof or r["close_ms"]%SLOT for r in rows):raise ValueError("clock")
    if any(b["close_ms"]-a["close_ms"]!=SLOT for a,b in zip(rows,rows[1:])):raise ValueError("gap")
    if any(type(r[k]) not in (float,int) or not math.isfinite(r[k]) for r in rows for k in ("spot_return","futures_return")):raise ValueError("numeric")
    def corr(x,y):
        if len(x)<12:return None
        mx=sum(x)/len(x);my=sum(y)/len(y)
        xx=sum((a-mx)**2 for a in x);yy=sum((b-my)**2 for b in y)
        return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(xx*yy) if xx and yy else None
    return {"pairs":max(0,len(rows)-1),"futures_leads_one_bar":corr([r["futures_return"] for r in rows[:-1]],[r["spot_return"] for r in rows[1:]]),
            "spot_leads_one_bar":corr([r["spot_return"] for r in rows[:-1]],[r["futures_return"] for r in rows[1:]]),"status":"DESCRIPTIVE_ONLY","prospective_admitted":False}
class Tests(unittest.TestCase):
    def test_asof(self):
        p={"event_ms":100,"seen_ms":101,"source_time_verified":True}
        self.assertEqual(admit({"TV_PRICE":p},100)["TV_PRICE"],"CLOCK_OR_LOOKAHEAD")
        self.assertEqual(admit({"TV_PRICE":p},101)["TV_PRICE"],"AVAILABLE_DESCRIPTIVE")
    def test_absorption(self):
        self.assertTrue(absorption(1.1,1.10001,80,100)["candidate"])
        self.assertFalse(absorption(1.1,1.101,80,100)["candidate"])
    def test_lag(self):
        r=[dict(close_ms=(i+1)*SLOT,seen_ms=(i+1)*SLOT,spot_return=i-1,futures_return=i) for i in range(14)]
        self.assertAlmostEqual(lead_lag(r,14*SLOT)["futures_leads_one_bar"],1)
        with self.assertRaises(ValueError):lead_lag(r[:2]+r[3:],14*SLOT)
if __name__=="__main__":unittest.main()
