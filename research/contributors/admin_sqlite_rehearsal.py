# REMURA Contributors v0.24 LAB — 16/11/2026 07:17 CET
"""In-memory SQLite rehearsal of closed privileged application and stale snapshot recovery.
Never accepts DB paths, D1 bindings, real identity records, secrets or network calls.
Independent journal and latest pin remain trusted inputs to this rehearsal.
"""
import sqlite3
from pathlib import Path
from recovery_journal_candidate import ZERO, HEX32, digest, verify, valid_hex, restore_plan, deny
from admin_identity_candidate import CLOSED, closure, exact_inventory, plan_change, reconcile
SCHEMA=(Path(__file__).parent/"d1_access_candidate.sql").read_text()
def event_row(e):
    return (e["seq"],digest(e),e["prev"],e["kind"],e["subject"],e["at"])
class AdminRehearsal:
    def __init__(self,generation,*,synthetic=False):
        if synthetic is not True or not valid_hex(generation,HEX32):deny()
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT INTO lab_generation VALUES(1,?,?)",(generation,ZERO))
        self.poisoned=False
    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def gates(self):
        rows=self.db.execute("SELECT write_enabled,read_enabled,recovery_enabled FROM lab_state WHERE id=1").fetchall()
        if rows!=[(0,0,0)]:deny()
        return dict(CLOSED)
    def pin(self):
        rows=self.db.execute("SELECT generation,journal_pin FROM lab_generation WHERE id=1").fetchall()
        if len(rows)!=1:deny()
        return rows[0]
    def inventory(self):
        rows=self.db.execute("SELECT subject,email_tag,'OWNER','owner',revoked FROM lab_owner UNION ALL SELECT subject,email_tag,'CONTRIBUTOR',slot,revoked FROM lab_identities").fetchall()
        return [dict(subject=s,email_tag=t,role=r,slot=l,revoked=bool(v)) for s,t,r,l,v in rows]
    def verify_prefix(self,events,pin):
        records=verify(events,pin)
        exact_inventory(records,self.inventory())
        audit=self.db.execute("SELECT seq,event_pin,prev_pin,kind,subject,at_utc FROM lab_admin_events ORDER BY seq").fetchall()
        if audit!=[event_row(e) for e in events]:deny()
        if self.db.execute("PRAGMA foreign_key_check").fetchall():deny()
        if self.db.execute("PRAGMA quick_check").fetchall()!=[("ok",)]:deny()
    def _transaction(self,fn):
        if self.poisoned or self.db.in_transaction:deny()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result=fn()
        except BaseException:
            try:self.db.execute("ROLLBACK")
            except BaseException:self.poisoned=True
            raise
        try:self.db.execute("COMMIT")
        except BaseException:
            # Ambiguous commit: do not reuse this instance, even if rollback seems possible.
            self.poisoned=True
            raise
        return result
    def _event(self,e):
        s,t,r,l=e["subject"],e["email_tag"],e["role"],e["slot"]
        if e["kind"]=="ENROLL":
            if r=="OWNER":self.db.execute("INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)",(s,t))
            else:self.db.execute("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)",(s,t,l))
        else:
            # Privileged closed revocation, audited here; not the HTTP recovery_enabled path.
            # Never change the immutable contribution owner or old approval decisions.
            if self.db.execute("SELECT 1 FROM lab_entries WHERE subject=? AND received_utc>? LIMIT 1",(s,e["at"])).fetchone():deny()
            if r=="OWNER":q="UPDATE lab_owner SET revoked=1 WHERE subject=? AND email_tag=? AND revoked=0"
            else:q="UPDATE lab_identities SET revoked=1 WHERE subject=? AND email_tag=? AND revoked=0"
            if self.db.execute(q,(s,t)).rowcount!=1:deny()
        self.db.execute("INSERT INTO lab_admin_events VALUES(?,?,?,?,?,?)",event_row(e))
    def _rotate(self,old,new,pin):
        if not valid_hex(new,HEX32) or old[0]==new:deny()
        if self.db.execute("UPDATE lab_generation SET generation=?,journal_pin=? WHERE id=1 AND generation=? AND journal_pin=?",(new,pin,*old)).rowcount!=1:deny()
    def apply(self,plan,events,external_pin,*,ingress_closed=False,quiesced=False,identity_verified=False,owner_authorized=False):
        """Journal append must have been committed and externally pinned BEFORE this method."""
        closure(self.gates(),ingress_closed,quiesced)
        if identity_verified is not True or owner_authorized is not True:deny()
        verify(events,external_pin)
        if not events or external_pin!=plan.get("new_pin"):deny()
        def work():
            old=self.pin();event=events[-1]
            self.verify_prefix(events[:-1],event["prev"])
            if old[1]!=event["prev"]:deny()
            expected=plan_change(events[:-1],event["prev"],self.inventory(),old[0],plan.get("generation"),
                kind=event["kind"],at=event["at"],subject=event["subject"],email_tag=event["email_tag"],role=event["role"],slot=event["slot"],
                gates=self.gates(),ingress_closed=ingress_closed,quiesced=quiesced,identity_verified=identity_verified,owner_authorized=owner_authorized)
            if expected!=plan:deny()
            self._event(event);self._rotate(old,plan["generation"],external_pin)
            self.verify_prefix(events,external_pin)
            return reconcile(events,external_pin,self.inventory(),expected_generation=plan["generation"],db_generation=self.pin()[0],db_pin=self.pin()[1],gates=self.gates(),ingress_closed=True,quiesced=True)
        return self._transaction(work)
    def copy_snapshot(self):
        """Copy ONLY this owned in-memory database. Not an external backup."""
        if self.poisoned or self.db.in_transaction:deny()
        other=AdminRehearsal(self.pin()[0],synthetic=True)
        try:self.db.backup(other.db)
        except BaseException:other.close();raise
        return other
    def recover(self,events,external_pin,new_generation,*,ingress_closed=False,quiesced=False):
        """Close restored flags first. Reject missing enrollment or stale journal; only replay missing revocations."""
        if ingress_closed is not True or quiesced is not True or self.poisoned or self.db.in_transaction:deny()
        verify(events,external_pin)
        # Never rely on snapshot gate values; close in a separate committed transaction.
        self._transaction(lambda:self.db.execute("UPDATE lab_state SET write_enabled=0,read_enabled=0,recovery_enabled=0 WHERE id=1"))
        def work():
            old=self.pin()
            pins=[ZERO]+[digest(e) for e in events]
            if old[1] not in pins:deny()
            n=pins.index(old[1]);self.verify_prefix(events[:n],old[1])
            proposed=restore_plan(events,external_pin,self.inventory(),old[0],new_generation,ingress_closed=True)
            tail=events[n:]
            if any(e["kind"]!="REVOKE" for e in tail):deny()
            if sorted(e["subject"] for e in tail)!=proposed["revoke_subjects"]:deny()
            for e in tail:self._event(e)
            self._rotate(old,new_generation,external_pin)
            self.verify_prefix(events,external_pin)
            return reconcile(events,external_pin,self.inventory(),expected_generation=new_generation,db_generation=self.pin()[0],db_pin=self.pin()[1],gates=self.gates(),ingress_closed=True,quiesced=True)
        return self._transaction(work)
