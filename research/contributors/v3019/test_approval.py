import sqlite3, pathlib
p=pathlib.Path(__file__).parent
# Minimal synthetic tables intentionally not full D1 schema.
db=sqlite3.connect(':memory:'); db.execute('PRAGMA foreign_keys=ON')
db.executescript('''
CREATE TABLE lab_owner(id INTEGER PRIMARY KEY, subject TEXT,email_tag TEXT,revoked INTEGER);
INSERT INTO lab_owner VALUES(1,'owner','email',0);
CREATE TABLE lab_state(id INTEGER PRIMARY KEY,read_enabled INTEGER,write_enabled INTEGER,recovery_enabled INTEGER);
INSERT INTO lab_state VALUES(1,1,1,0);
CREATE TABLE lab_identities(subject TEXT PRIMARY KEY,email_tag TEXT,revoked INTEGER,slot TEXT);
INSERT INTO lab_identities VALUES('b','btag',0,'friend-b'),('a','atag',0,'friend-a');
CREATE TABLE lab_level_catalog_v110(market TEXT,provider TEXT,ticker TEXT,product TEXT,contract TEXT,source_group TEXT,active INTEGER);
INSERT INTO lab_level_catalog_v110 VALUES('NQ','RITHMIC','NQ_CONT','FUTURE','CONTINUOUS','SG',1);
CREATE TABLE lab_telegram_policy_v3012(id INTEGER PRIMARY KEY,enabled INTEGER,epoch INTEGER);
INSERT INTO lab_telegram_policy_v3012 VALUES(1,0,1);
CREATE TABLE lab_telegram_sources_v3012(market TEXT,provider TEXT,ticker TEXT,product TEXT,contract TEXT);
INSERT INTO lab_telegram_sources_v3012 VALUES('NQ','RITHMIC','NQ_CONT','FUTURE','CONTINUOUS');
CREATE TABLE lab_level_attempts_v110(id INTEGER PRIMARY KEY);
CREATE TABLE lab_proposals_v3019(id INTEGER PRIMARY KEY,subject TEXT,email_tag TEXT,market TEXT,provider TEXT,ticker TEXT,product TEXT,contract TEXT,source_group TEXT,publication_mode TEXT);
CREATE TABLE lab_proposal_outbox_v3019(proposal_id INTEGER PRIMARY KEY,epoch INTEGER,state TEXT,queued_utc TEXT);
CREATE TRIGGER lab_proposal_enqueue_v3019 AFTER INSERT ON lab_proposals_v3019 BEGIN SELECT 1; END;
''')
db.executescript((p/'proposal-approval.sql').read_text())
n=0
def check(x):
 global n
 assert x; n+=1
def one(sql):return db.execute(sql).fetchone()[0]
def submit(i,mode='TELEGRAM',subject='b',tag='btag'):
 db.execute("INSERT INTO lab_proposals_v3019 VALUES(?,?,?,'NQ','RITHMIC','NQ_CONT','FUTURE','CONTINUOUS','SG',?)",(i,subject,tag,mode))
def policy(mode):db.execute('UPDATE lab_approval_policy_v3019 SET mode=?,revision=revision+1',(mode,))
def toggle(enabled):db.execute('UPDATE lab_telegram_policy_v3012 SET enabled=?,epoch=epoch+?',(enabled,enabled))
def review(i,action='APPROVED',actor='owner'):
 db.execute("INSERT INTO lab_proposal_decision_v3019(proposal_id,action,origin,actor_subject,actor_email_tag,reason) VALUES(?,?,'OWNER',?,'email','review')",(i,action,actor))
def denied(fn):
 try:fn()
 except sqlite3.IntegrityError:check(True)
 else:raise AssertionError('not denied')
def queued(i):return one(f'SELECT COUNT(*) FROM lab_proposal_outbox_v3019 WHERE proposal_id={i}')
def decided(i):return one(f'SELECT COUNT(*) FROM lab_proposal_decision_v3019 WHERE proposal_id={i}')
check(one('SELECT mode FROM lab_approval_policy_v3019')=='AUTOMATIC')
submit(1);check(decided(1)==1 and queued(1)==0)
toggle(1);check(queued(1)==0)
submit(2);check(decided(2)==1 and queued(2)==1)
submit(3,'TEST','a','atag');check(decided(3)==1 and queued(3)==0)
policy('MANUAL');submit(4);check(decided(4)==0 and queued(4)==0)
review(4);check(decided(4)==1 and queued(4)==1)
denied(lambda:review(4));check(queued(4)==1)
submit(5);review(5,'REJECTED');check(decided(5)==1 and queued(5)==0)
submit(6);policy('AUTOMATIC');check(decided(6)==0 and queued(6)==0)
review(6);check(queued(6)==1)
policy('MANUAL');submit(7);toggle(0);toggle(1);review(7);check(queued(7)==0)
toggle(0);submit(8);review(8);check(decided(8)==1 and queued(8)==0)
submit(9);toggle(1);review(9);check(queued(9)==0)
submit(10);denied(lambda:review(10,actor='intruder'));check(decided(10)==0)
db.execute('UPDATE lab_state SET write_enabled=0');denied(lambda:review(10));denied(lambda:policy('AUTOMATIC'))
db.execute('UPDATE lab_state SET write_enabled=1');review(10);check(queued(10)==1)
denied(lambda:db.execute('INSERT INTO lab_level_attempts_v110 VALUES(1)'))
denied(lambda:db.execute('DELETE FROM lab_proposal_decision_v3019'))
denied(lambda:db.execute('UPDATE lab_policy_audit_v3019 SET new_value=\'x\''))
check(one('SELECT COUNT(*) FROM lab_policy_audit_v3019')==8)
print(f'{n}/{n} approval assertions PASS; SQLite {sqlite3.sqlite_version}; synthetic base only')
