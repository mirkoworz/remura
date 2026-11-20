# REMURA v0.8.119 LAB — 17/11/2026 CET
"""Offline subprocess bridge: exact candidate SQL only, disposable fixture DB."""
import json,re,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).parent
def sql(name,file):
    return re.search(name+r" = \x60([\s\S]+?)\x60;",(ROOT/file).read_text()).group(1)
ALLOWED={
 sql("RESERVE_SQL","level_admission_candidate.mjs").replace("RETURNING enabled,allowed","RETURNING enabled,allowed,attempts"),
 sql("STOP_SQL","level_admission_candidate.mjs"),
 sql("INSERT_SQL","level_receipt_candidate.mjs"),
 sql("EXISTING_SQL","level_receipt_candidate.mjs")}
def main():
    path=Path(sys.argv[1]).resolve(strict=True)
    if path.name!="remura-level-e2e-fixture.sqlite" or path.is_symlink():raise ValueError("fixture only")
    raw=sys.stdin.read(50001)
    if len(raw)>50000:raise ValueError("fixture bound")
    q=json.loads(raw)
    if type(q) is not dict or set(q)!={"sql","args"} or q["sql"] not in ALLOWED or type(q["args"]) is not list or len(q["args"])>13:raise ValueError("query denied")
    db=sqlite3.connect(path.as_uri()+"?mode=rw",uri=True,timeout=2)
    try:
        db.row_factory=sqlite3.Row
        with db:
            row=db.execute(q["sql"],q["args"]).fetchone()
            result=None if row is None else dict(row)
        print(json.dumps(result))
    finally:db.close()
if __name__=="__main__":main()
