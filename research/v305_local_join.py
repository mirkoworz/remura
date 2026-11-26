"""V30.5 LAB — local-only aggregate join; input via private pipe."""
import sys,os,json,sqlite3,time
from pathlib import Path
BASE=Path.home()/".remura-v296"
sys.path[:0]=[str(BASE/"v301"),str(BASE)]
from v297_bounded_collector import check_private
from v299_source_correlation import observe
from v304_source_context import combine_report
def run():
    check_private(BASE,True)
    target=BASE/"tv-custody.sqlite3"
    check_private(target)
    source=BASE/"v301"/"v303-public-cot.json"
    check_private(source)
    cot=json.loads(source.read_text())
    raw=sys.stdin.buffer.read(4000001)
    if len(raw)>4000000:raise ValueError("size")
    inp=json.loads(raw)
    symbol,provider,broker,updated,payload=inp["price"]
    p=json.loads(payload)
    if symbol!="EURUSD" or provider!="ctrader" or not broker or p.get("providerSymbol")!=broker:
        raise ValueError("identity")
    captured=inp["captured_ms"]
    asof=int(time.time()*1000)
    if type(captured) is not int or not 0<=asof-captured<=30000:raise ValueError("capture")
    db=sqlite3.connect(target.as_uri()+"?mode=ro",uri=True,timeout=3)
    try:
        db.execute("PRAGMA query_only=ON")
        rows=db.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
        WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) > ?
        AND CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)<=?
        ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 289""",(asof-86400000,asof)).fetchall()
    finally:db.close()
    if len(rows)>288:raise ValueError("capacity")
    records=[{"metadata":json.loads(m),"original":v,"sha256":h} for m,v,h in rows]
    report=observe(records,cot,p,updated,captured,asof,symbol=symbol)
    out=combine_report(report,cot,inp["retail"],captured,asof)
    print(json.dumps({"status":"DESCRIPTIVE_ONLY","footprint_status":out["footprint"]["status"],
       "footprint_segment_bars":out["footprint"].get("segment_bars",0),
       "available_level_count":len(out["levels"]),"price_status":out["price"]["status"],
       "cot_status":out["cot"]["status"],"independent_usd_leg":out["cot"].get("independent_usd_leg","UNAVAILABLE"),
       "sentiment_status":out["sentiment"]["status"],"vendor_freshness_verified":False,
       "prospective_admitted":False},sort_keys=True))
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("V305 CORRELATION STOP",type(e).__name__);sys.exit(2)
