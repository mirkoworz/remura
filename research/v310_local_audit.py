"""V31.0 LAB — aggregate-only local audit, no writes, no external calls.
Run on Oracle under the existing owner account.
"""
import json,sqlite3,time,sys,stat,os
from pathlib import Path
from datetime import datetime
from collections import Counter
from v310_multifeed import tv_bar,m15,compare,CT,M15
def ms(v):
    t=datetime.fromisoformat(v.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone")
    return int(t.timestamp()*1000)
def audit():
    p=Path.home()/".remura-v296"/"tv-custody.sqlite3"
    for path,mode,kind in ((p.parent,0o700,stat.S_ISDIR),(p,0o600,stat.S_ISREG)):
        s=path.lstat()
        if not kind(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=mode:raise ValueError("custody_permissions")
    now=int(time.time()*1000)
    db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3)
    try:
        db.execute("PRAGMA query_only=ON")
        rows=db.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
           ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) DESC LIMIT 576""").fetchall()
    finally:db.close()
    good=[];bad=Counter()
    for m,raw,h in rows:
        try:good.append(tv_bar(json.loads(m),raw,h,now))
        except (ValueError,KeyError,TypeError,ArithmeticError) as e:
            bad[type(e).__name__]+=1
    counts=Counter(b["open_ms"] for b in good)
    unique=[b for b in good if counts[b["open_ms"]]==1]
    agg=m15(unique,now)
    print(json.dumps({"webhooks_sampled":len(rows),"valid_ohlc_m5":len(good),
        "rejected":sum(bad.values()),"duplicate_slots":sum(n>1 for n in counts.values()),
        "complete_m15":len(agg),"latest_m5_age_seconds":round((now-max(b["close_ms"] for b in unique))/1000) if unique else None,
        "latest_m15_age_seconds":round((now-max(b["close_ms"] for b in agg))/1000) if agg else None},sort_keys=True),flush=True)
    data=sys.stdin.buffer.read(4000001)
    if not data or len(data)>4000000:raise ValueError("price_input")
    item=json.loads(data);capture=item["captured_ms"]
    symbol,source,broker,updated,payload=item["price"]
    doc=json.loads(payload);u=ms(updated)
    if symbol!="EURUSD" or source!="ctrader" or not broker or doc.get("providerSymbol")!=broker or doc.get("provider")!="ctrader" or not 0<u<=capture<=now+30000 or abs(capture-now)>30000:raise ValueError("price_identity_clock")
    ct=[]
    if agg:
        first,last=agg[0]["open_ms"],agg[-1]["close_ms"]
        for v in doc["timeframes"]["M15"]:
            t=ms(v["t"])
            if first<=t and t+M15<=min(last,u):
                ct.append({"source":CT,"open_ms":t,"close_ms":t+M15,"available_ms":capture,**{k:v[k] for k in ("o","h","l","c")}})
    result=compare(agg,ct,max(now,capture))
    result["ctrader_snapshot_age_seconds"]=round((capture-u)/1000)
    print(json.dumps(result,sort_keys=True),flush=True)
if __name__=="__main__":
    try:audit()
    except Exception as e:
        print("V310 AUDIT STOP",type(e).__name__);sys.exit(2)
