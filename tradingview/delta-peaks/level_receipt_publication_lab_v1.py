# REMURA v0.8.127 LAB — 17/11/2026 CET
"""Bounded atomic synthetic custody journal in a separate memory-only DB.
No real independent authority, migration, persistent publication or restore.
"""
import sqlite3,json,hmac
from level_receipt_custody_lab_v1 import canonical,hashobj,hex64,need
from level_receipt_witness_lab_v1 import genesis,advance,verify_witness,generation,key_ok,ZERO
LIMIT=128
FLAGS=dict(synthetic=True,ingress_closed=True)
DDL="""CREATE TABLE custody_fixture(seq INTEGER PRIMARY KEY CHECK(seq BETWEEN 1 AND 128),
generation TEXT NOT NULL UNIQUE, anchor TEXT NOT NULL UNIQUE, snapshot_pin TEXT NOT NULL UNIQUE,
record TEXT NOT NULL)"""
def scope(db,synthetic,ingress_closed):
    need(synthetic is True and ingress_closed is True and isinstance(db,sqlite3.Connection) and not db.in_transaction)
    need([tuple(r) for r in db.execute("PRAGMA database_list")] in ([(0,"main","")],[(0,"main",""),(1,"temp","")]))
    need(db.execute("SELECT 1 FROM temp.sqlite_master LIMIT 1").fetchone() is None)
def schema(db):
    return [tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM main.sqlite_master ORDER BY type,name LIMIT 10")]
def expected_schema():
    db=sqlite3.connect(":memory:")
    try:
        db.execute(DDL)
        return schema(db)
    finally:db.close()
def init(db,*,synthetic=False,ingress_closed=False):
    scope(db,synthetic,ingress_closed)
    db.execute("BEGIN IMMEDIATE")
    try:
        need(schema(db)==[])
        db.execute(DDL)
        db.commit()
    except BaseException:
        db.rollback()
        raise
def chain(db,key):
    need(key_ok(key) and schema(db)==expected_schema())
    rows=db.execute("SELECT seq,generation,anchor,snapshot_pin,record FROM main.custody_fixture ORDER BY seq LIMIT ?",(LIMIT+1,)).fetchall()
    need(len(rows)<=LIMIT)
    previous=ZERO; generations=set(); pins=set(); result=None
    for i,(seq,gen,anchor,pin,raw) in enumerate(rows,1):
        need(seq==i and generation(gen) and gen not in generations and pin not in pins and hex64(anchor))
        need(type(raw) is str and len(raw)<=2048)
        record=json.loads(raw)
        need(canonical(record).decode("ascii")==raw)
        verified=verify_witness(record,key,latest_anchor=anchor,latest_generation=gen,latest_sequence=seq,**FLAGS)
        need(record["body"]["previous_anchor"]==previous and verified==pin)
        previous=anchor;generations.add(gen);pins.add(pin);result=(record,anchor)
    return result,generations,pins
def publish(db,key,*,expected_anchor,new_generation,new_snapshot_pin,synthetic=False,ingress_closed=False):
    scope(db,synthetic,ingress_closed)
    need(hex64(expected_anchor) and generation(new_generation) and hex64(new_snapshot_pin))
    # The lock encloses both verification and insert. No retry on conflict.
    db.execute("BEGIN IMMEDIATE")
    try:
        current,gens,pins=chain(db,key)
        actual=ZERO if current is None else current[1]
        need(hmac.compare_digest(actual,expected_anchor))
        need(new_generation not in gens and new_snapshot_pin not in pins and len(gens)<LIMIT)
        if current is None:
            record,anchor=genesis(new_snapshot_pin,new_generation,key,**FLAGS)
        else:
            prev,old_anchor=current
            record,anchor=advance(prev,key,latest_anchor=old_anchor,latest_generation=prev["body"]["generation"],latest_sequence=prev["body"]["sequence"],new_generation=new_generation,new_snapshot_pin=new_snapshot_pin,**FLAGS)
        db.execute("INSERT INTO main.custody_fixture VALUES(?,?,?,?,?)",(record["body"]["sequence"],new_generation,anchor,new_snapshot_pin,canonical(record).decode("ascii")))
        db.commit()
        return record,anchor
    except BaseException:
        db.rollback()
        raise
def latest(db,key,*,expected_anchor,synthetic=False,ingress_closed=False):
    scope(db,synthetic,ingress_closed)
    need(hex64(expected_anchor))
    db.execute("BEGIN")
    try:
        current,_,_=chain(db,key)
        need(current is not None and hmac.compare_digest(current[1],expected_anchor))
        return current
    finally:db.rollback()
