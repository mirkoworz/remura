"""V30.3 aggregate-only local correlation CLI, 26/11/2026.
Price row arrives on a private local pipe, never printed or saved.
"""
import sys,os,json,sqlite3
from pathlib import Path
BASE=Path.home()/".remura-v296"
sys.path.insert(0,str(BASE))
sys.path.insert(0,str(BASE/"v301"))
from v302_descriptive_adapter import describe
from v297_bounded_collector import check_private

def run():
    check_private(BASE,True)
    target=BASE/"tv-custody.sqlite3"
    check_private(target)
    source=BASE/"v301"/"v303-public-cot.json"
    check_private(source)
    cot=json.loads(source.read_text())
    data=sys.stdin.buffer.read(4000001)
    if len(data)>4000000:raise ValueError("size")
    row=json.loads(data)
    if row is not None and (type(row) is not list or len(row)!=5):
        raise ValueError("row")
    with sqlite3.connect(":memory:") as p, sqlite3.connect(target.as_uri()+"?mode=ro",uri=True) as c:
        p.execute("CREATE TABLE prices(symbol,source,broker_symbol,updated_at,payload)")
        if row is not None:p.execute("INSERT INTO prices VALUES (?,?,?,?,?)",row)
        p.commit()
        p.execute("PRAGMA query_only=ON")
        c.execute("PRAGMA query_only=ON")
        print(json.dumps(describe(c,p,cot),sort_keys=True))
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("CORRELAZIONE_STOP",type(e).__name__);sys.exit(2)
