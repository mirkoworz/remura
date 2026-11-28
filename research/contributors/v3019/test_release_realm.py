"""SQLite realm gate only; synthetic database; no network."""
import sqlite3
from pathlib import Path
sql=Path(__file__).with_name('proposal-release-realm.sql').read_text()
base='''CREATE TABLE lab_proposals_v3019(id INTEGER PRIMARY KEY); CREATE TABLE lab_proposal_outbox_v3019(id INTEGER PRIMARY KEY); CREATE TABLE lab_state(id INTEGER PRIMARY KEY,read_enabled INTEGER,write_enabled INTEGER,recovery_enabled INTEGER); INSERT INTO lab_state VALUES(1,1,0,0); CREATE TABLE lab_telegram_policy_v3012(id INTEGER PRIMARY KEY,enabled INTEGER); INSERT INTO lab_telegram_policy_v3012 VALUES(1,0);'''
n=0
def check(x):
 global n
 assert x;n+=1
def db():
 d=sqlite3.connect(':memory:'); d.executescript(base);return d
for change in ['UPDATE lab_state SET write_enabled=1','UPDATE lab_state SET read_enabled=0','UPDATE lab_state SET recovery_enabled=1','UPDATE lab_telegram_policy_v3012 SET enabled=1','INSERT INTO lab_proposals_v3019 VALUES(1)','INSERT INTO lab_proposal_outbox_v3019 VALUES(1)','DELETE FROM lab_state','DELETE FROM lab_telegram_policy_v3012']:
 d=db();d.execute(change);d.commit()
 try:d.executescript('BEGIN;\n'+sql+'\nCOMMIT;');raise AssertionError(change)
 except sqlite3.IntegrityError:
  d.rollback();check(d.execute("SELECT count(*) FROM sqlite_schema WHERE name='lab_delivery_realm_v3019'").fetchone()[0]==0)
 d.close()
d=db();d.executescript('BEGIN;\n'+sql+'\nCOMMIT;');check(d.execute('SELECT realm FROM lab_delivery_realm_v3019').fetchone()[0]=='STAGING_CANDIDATE')
for change in ["UPDATE lab_delivery_realm_v3019 SET realm='STAGING_CANDIDATE'",'DELETE FROM lab_delivery_realm_v3019',"INSERT OR REPLACE INTO lab_delivery_realm_v3019 VALUES(1,'STAGING_CANDIDATE')"]:
 try:d.execute(change);raise AssertionError(change)
 except sqlite3.IntegrityError:check(True)
check(d.execute('SELECT count(*) FROM lab_delivery_realm_v3019').fetchone()[0]==1)
print(f'{n}/{n} realm checks passed SQLite {sqlite3.sqlite_version}')
