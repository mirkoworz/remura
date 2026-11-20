# REMURA v0.8.121 LAB — 17/11/2026 07:04 CET (session start)
"""Exact SQL only, isolated disposable fixture. No cloud or real endpoint."""
import json,re,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).parent
def sql(name,file):
    return re.search(name+r" = \x60([\s\S]+?)\x60;",(ROOT/file).read_text()).group(1)
ALLOWED={
 sql("RESERVE_SQL","level_admission_candidate.mjs").replace("RETURNING enabled,allowed","RETURNING enabled,allowed,attempts"),
 sql("STOP_SQL","level_admission_candidate.mjs"),
 sql("FINALIZE_SQL","level_permit_ledger_candidate.mjs")}
def main():
    given=Path(sys.argv[1])
    if given.is_symlink() or given.name!="remura-level-permits-worker-fixture.sqlite":raise ValueError("fixture only")
    path=given.resolve(strict=True)
    raw=sys.stdin.read(50001)
    if len(raw)>50000:raise ValueError("fixture bound")
    q=json.loads(raw)
    if type(q) is not dict or set(q)!={"sql","args"} or q["sql"] not in ALLOWED or type(q["args"]) is not list or len(q["args"])>14:raise ValueError("query denied")
    db=sqlite3.connect(path.as_uri()+"?mode=rw",uri=True,timeout=2)
    try:
        db.row_factory=sqlite3.Row
        with db:
            rows=db.execute(q["sql"],q["args"]).fetchall()
            if len(rows)>1:raise ValueError("unexpected rows")
        print(json.dumps(dict(rows[0]) if rows else None))
    finally:db.close()
if __name__=="__main__":main()
