"""REMURA V30.0 LAB — durable, conservative local daily request accounting.
Separate SQLite DB. The quota is this collector's allocation, NOT total D1 usage.
No automatic reset of unresolved requests; no automatic retries.
"""
import sqlite3
from datetime import date
class Budget:
    def __init__(self,db,max_selects,max_rows):
        if type(max_selects) is not int or not 1<=max_selects<=400 or type(max_rows) is not int or not 10000<=max_rows<=1000000:
            raise ValueError("budget_limits")
        self.db=db
        self.max_selects=max_selects
        self.max_rows=max_rows
        names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if names-{"quota_requests"}:raise ValueError("not_quota_db")
        db.execute("""CREATE TABLE IF NOT EXISTS quota_requests(
        id INTEGER PRIMARY KEY, day TEXT NOT NULL, reserved INTEGER NOT NULL,
        actual INTEGER, finished INTEGER NOT NULL DEFAULT 0)""")
        db.commit()
    def reserve(self,day,amount):
        if date.fromisoformat(day).isoformat()!=day or amount!=10000:
            raise ValueError("budget_request")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if self.db.execute("SELECT 1 FROM quota_requests WHERE finished=0 LIMIT 1").fetchone():
                raise ValueError("unresolved_request")
            n,total=self.db.execute("SELECT COUNT(*),COALESCE(SUM(COALESCE(actual,reserved)),0) FROM quota_requests WHERE day=?",(day,)).fetchone()
            if n>=self.max_selects or total+amount>self.max_rows:
                raise ValueError("daily_budget")
            i=self.db.execute("INSERT INTO quota_requests(day,reserved) VALUES (?,?)",(day,amount)).lastrowid
            self.db.commit()
            return i
        except BaseException:
            self.db.rollback();raise
    def finish(self,i,actual):
        if type(actual) is not int or actual<0:raise ValueError("actual")
        with self.db:
            cur=self.db.execute("UPDATE quota_requests SET actual=?,finished=1 WHERE id=? AND finished=0",(actual,i))
            if cur.rowcount!=1:raise ValueError("reservation")
