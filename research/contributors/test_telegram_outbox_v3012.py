"""Offline SQLite fixture for the additive Telegram migration; no D1/network."""
import sqlite3
from pathlib import Path

sql = Path(__file__).with_name('telegram-outbox-v3012.sql').read_text()
db = sqlite3.connect(':memory:')
db.executescript('''
PRAGMA foreign_keys=ON;
CREATE TABLE lab_identities(subject TEXT PRIMARY KEY,email_tag TEXT,slot TEXT,revoked INTEGER);
CREATE TABLE lab_level_catalog_v110(market TEXT,provider TEXT,ticker TEXT,product TEXT,contract TEXT,PRIMARY KEY(market,provider,ticker,product,contract));
CREATE TABLE lab_level_attempts_v110(id INTEGER PRIMARY KEY,subject TEXT,email_tag TEXT,market TEXT,provider TEXT,ticker TEXT,product TEXT,contract TEXT,duplicate_of INTEGER,note TEXT,received_utc TEXT);
INSERT INTO lab_identities VALUES ('a','a','friend-a',0),('b','b','friend-b',0),('c','c','friend-c',0),('r','r','friend-c',1);
INSERT INTO lab_level_catalog_v110 VALUES ('EURUSD','FIXTURE','EURUSD','SPOT',''),('EURUSD','ECB','EURUSD','SPOT',''),('EURUSD','OTHER','EURUSD','SPOT','');
''')
now = '2026-11-26T11:00:00Z'
def level(i, subject='b', provider='FIXTURE', duplicate=None, note=''):
    db.execute('INSERT INTO lab_level_attempts_v110 VALUES (?,?,?,?,?,?,?,?,?,?,?)',(i,subject,subject,'EURUSD',provider,'EURUSD','SPOT','',duplicate,note,now))
def queued():
    return db.execute('SELECT receipt_id,state FROM lab_telegram_outbox_v3012 ORDER BY receipt_id').fetchall()
def reject(sql):
    try: db.execute(sql)
    except sqlite3.IntegrityError: return
    raise AssertionError('Unexpectedly accepted: '+sql)
level(1)
db.executescript(sql)
assert queued()==[] and db.execute('SELECT enabled,epoch,start_after_receipt FROM lab_telegram_policy_v3012').fetchone()==(0,1,1)
print('PASS historical excluded / default OFF')
db.execute("INSERT INTO lab_telegram_sources_v3012 VALUES ('EURUSD','FIXTURE','EURUSD','SPOT','')")
level(2)
assert queued()==[]
print('PASS disabled receipt preserved')
reject('UPDATE lab_telegram_policy_v3012 SET enabled=1')
reject('UPDATE lab_telegram_policy_v3012 SET enabled=1,epoch=2,start_after_receipt=1')
db.execute('UPDATE lab_telegram_policy_v3012 SET enabled=1,epoch=2,start_after_receipt=2')
print('PASS activation boundary guarded')
level(3)
assert queued()==[(3,'PENDING')]
print('PASS new canonical queued')
level(4,duplicate=3)
assert queued()==[(3,'PENDING')]
print('PASS duplicate not queued')
level(5,subject='a'); level(6,subject='r'); level(7,provider='ECB'); level(8,provider='OTHER'); level(9,note='TEST V30.9'); level(10,note='NON OPERATIVO')
assert queued()==[(3,'PENDING')]
print('PASS test / revoked / unknown source excluded')
db.execute("UPDATE lab_telegram_outbox_v3012 SET state='SENDING',claimed_utc=? WHERE receipt_id=3 AND state='PENDING'",(now,))
assert db.execute("UPDATE lab_telegram_outbox_v3012 SET state='SENDING',claimed_utc=? WHERE receipt_id=3 AND state='PENDING'",(now,)).rowcount==0
print('PASS claim only once (sequential SQL)')
db.execute("UPDATE lab_telegram_outbox_v3012 SET state='SENT',finished_utc=?,telegram_message_id=42 WHERE receipt_id=3",(now,))
reject("UPDATE lab_telegram_outbox_v3012 SET state='PENDING',claimed_utc=NULL,finished_utc=NULL,telegram_message_id=NULL WHERE receipt_id=3")
reject('DELETE FROM lab_telegram_outbox_v3012 WHERE receipt_id=3')
print('PASS terminal state / immutable outbox')
db.execute('UPDATE lab_telegram_policy_v3012 SET enabled=0')
level(11)
assert queued()==[(3,'SENT')]
db.execute('UPDATE lab_telegram_policy_v3012 SET enabled=1,epoch=3,start_after_receipt=11')
level(12,subject='c')
assert queued()==[(3,'SENT'),(12,'PENDING')]
print('PASS disable / re-enable without replay')
# Both inserts are one statement through the trigger: a rollback reverts both.
db.commit()
db.execute('BEGIN'); level(13); db.rollback()
assert db.execute('SELECT COUNT(*) FROM lab_level_attempts_v110 WHERE id=13').fetchone()==(0,)
assert queued()==[(3,'SENT'),(12,'PENDING')]
print('PASS atomic enqueue rollback')
print('10/10 fixture groups passed')
