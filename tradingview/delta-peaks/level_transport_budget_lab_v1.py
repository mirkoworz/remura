# REMURA v0.8.113 LAB — 17/11/2026 06:44 CET
"""Synthetic shared attempt budget, one local receipt database; no actual HTTP or cloud.
Initialization is explicit and only on an empty fixture session. Never expose this.
"""
import sqlite3
from level_local_probe_v1 import clock,need
from level_transport_http_lab_v1 import Adapter,MAX_ATTEMPTS,WINDOW_LIMIT,WINDOW_MS
from level_transport_sqlite_lab_v1 import PersistentReceiver

DDL="""CREATE TABLE attempt_budget (
 id INTEGER PRIMARY KEY CHECK(id=1), pin TEXT NOT NULL,
 total INTEGER NOT NULL CHECK(total BETWEEN 0 AND 48),
 last_ms INTEGER, window_count INTEGER NOT NULL CHECK(window_count BETWEEN 0 AND 20)
)"""

class SharedBudget:
    def __init__(self,receiver,*,initialize=False,synthetic=False):
        need(synthetic is True and type(initialize) is bool)
        need(type(receiver) is PersistentReceiver)
        self.receiver=receiver
        with receiver._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if initialize:
                enabled,rows=receiver._check(db)
                need(enabled and not rows)
                # No IF NOT EXISTS or reset; a second initialization fails.
                db.execute(DDL)
                db.execute("INSERT INTO attempt_budget VALUES(1,?,0,NULL,0)",(receiver.pin,))
            self._state(db)
    def _state(self,db):
        s=db.execute("SELECT id,pin,enabled FROM session LIMIT 2").fetchall()
        need(len(s)==1 and s[0][0]==1 and s[0][1]==self.receiver.pin and s[0][2] in (0,1))
        rows=db.execute("SELECT id,pin,total,last_ms,window_count FROM attempt_budget LIMIT 2").fetchall()
        need(len(rows)==1)
        ident,pin,total,last,count=rows[0]
        need(ident==1 and pin==self.receiver.pin)
        need(type(total) is int and type(count) is int and 0<=count<=min(total,WINDOW_LIMIT) and total<=MAX_ATTEMPTS)
        need((total==0 and last is None and count==0) or (total>0 and last is not None and count>0))
        if last is not None: clock(last,whole_second=False)
        return bool(s[0][2]),total,last,count
    def reserve(self,now):
        try:
            now=clock(now,whole_second=False)
            with self.receiver._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                enabled,total,last,count=self._state(db)
                if not enabled:return "OFF"
                if last is not None and now<last:
                    db.execute("UPDATE session SET enabled=0 WHERE id=1")
                    return "CLOCK_UNAVAILABLE"
                if total>=MAX_ATTEMPTS:return "RATE_LIMIT"
                if last is None or now//WINDOW_MS!=last//WINDOW_MS:count=0
                allowed=count<WINDOW_LIMIT
                db.execute("UPDATE attempt_budget SET total=?,last_ms=?,window_count=? WHERE id=1",
                           (total+1,now,count+int(allowed)))
                return "RESERVED" if allowed else "RATE_LIMIT"
        except (sqlite3.Error,OSError,ValueError,TypeError,OverflowError):
            return "STORAGE_UNAVAILABLE"
    def summary(self):
        with self.receiver._connection() as db:
            db.execute("BEGIN")
            enabled,total,last,count=self._state(db)
            return {"attempts":total,"window_count":count,"enabled":enabled,
                    "synthetic":True,"cloud_shared":False,"receipt_authenticated":False,
                    "operational_signal":False}

class SharedAdapter(Adapter):
    """Reuses v1 authentication and HTTP-shape parsing; replaces only admission.
    STOP is the same persistent session state as receipt writes. Reservation and
    receipt are separate transactions, so crashes may consume unused allowance.
    """
    def __init__(self,receiver,*,budget,key_hash,now,enabled=False,synthetic=False):
        super().__init__(receiver,key_hash=key_hash,now=now,enabled=enabled,synthetic=synthetic)
        need(type(budget) is SharedBudget and budget.receiver is receiver)
        self.budget=budget
    def _admit(self):
        try:now=clock(self._now(),whole_second=False)
        except (ValueError,TypeError,OverflowError):return "CLOCK_UNAVAILABLE"
        status=self.budget.reserve(now)
        return None if status=="RESERVED" else status
