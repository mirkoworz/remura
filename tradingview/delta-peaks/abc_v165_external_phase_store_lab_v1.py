"""REMURA v0.8.170 LAB — 18/11/2026, sessione successiva alle 16:54 CET.
Disposable owner-side persistent receipt register. No live deployment, signing,
installation, restore or independent storage attestation.
Caller must retain the latest anchor outside the server and this LAB database.
"""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from abc_v165_external_phase_receipt_lab_v1 import (
    ZERO, anchor, validate, verify, successor, need, hex64, canon)

def path_for(directory,synthetic):
    need(synthetic is True)
    directory=Path(directory)
    need(directory.is_absolute() and directory==directory.resolve()
         and Path(tempfile.gettempdir()).resolve() in directory.parents)
    s=directory.lstat()
    need(stat.S_ISDIR(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077)
    return directory/"phase-register.sqlite3"

def create(directory,*,synthetic=False):
    p=path_for(directory,synthetic)
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.close(fd)
    with closing(sqlite3.connect(p)) as db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE receipts(seq INTEGER PRIMARY KEY, body BLOB NOT NULL, signature BLOB NOT NULL, pin TEXT NOT NULL UNIQUE)")
        db.commit()
    fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

def verify_one(body,sig,pin,keyring,signer):
    verify(body,sig,keyring=keyring,signer=signer,latest_anchor=pin,
           transaction=body["transaction"],plan=body["plan"],
           sequence=body["sequence"],phase=body["phase"],
           journal=body["journal"],challenge=body["challenge"],synthetic=True)

def history(db,keyring,signer):
    rows=db.execute("SELECT seq,body,signature,pin FROM receipts ORDER BY seq LIMIT 6").fetchall()
    need(len(rows)<=5)
    previous=None
    latest=ZERO
    challenges=set()
    for i,(seq,raw,sig,pin) in enumerate(rows,1):
        need(type(raw) is bytes and 0<len(raw)<=4096)
        body=json.loads(raw)
        validate(body)
        need(canon(body)==raw and seq==i==body["sequence"]
             and body["previous"]==latest and body["challenge"] not in challenges)
        if previous is not None:
            old,old_sig=previous
            need(body==successor(old,old_sig,latest_anchor=latest,
                 phase=body["phase"],journal=body["journal"],challenge=body["challenge"]))
        verify_one(body,sig,pin,keyring,signer)
        challenges.add(body["challenge"])
        latest=pin
        previous=(body,sig)
    return previous,latest,challenges

def append(directory,body,signature,*,expected_latest,keyring,signer,synthetic=False):
    p=path_for(directory,synthetic)
    s=p.lstat()
    need(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid()
         and s.st_nlink==1 and not s.st_mode&0o077 and hex64(expected_latest))
    validate(body)
    pin=anchor(body,signature)
    with closing(sqlite3.connect(p.as_uri()+"?mode=rw",uri=True,timeout=1)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA synchronous=FULL")
        need(db.execute("PRAGMA journal_mode").fetchone()==("delete",))
        db.execute("BEGIN IMMEDIATE")
        try:
            previous,latest,challenges=history(db,keyring,signer)
            need(latest==expected_latest and body["previous"]==latest
                 and body["challenge"] not in challenges)
            if previous is None:
                need(body["sequence"]==1 and body["phase"]=="prepared")
            else:
                old,old_sig=previous
                need(body==successor(old,old_sig,latest_anchor=latest,
                    phase=body["phase"],journal=body["journal"],challenge=body["challenge"]))
            verify_one(body,signature,pin,keyring,signer)
            db.execute("INSERT INTO receipts VALUES (?,?,?,?)",
                       (body["sequence"],canon(body),signature,pin))
            db.commit()
        except BaseException:
            db.rollback()
            raise
    # Private caller return only; never log pins or signed receipts.
    return pin
