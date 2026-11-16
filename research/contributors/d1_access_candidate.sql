-- REMURA Contributors v0.20 LAB — 16/11/2026 07:02 CET
-- Fresh EMPTY candidate only, derived from v0.19; never migrate or copy fixture records. NO DEPLOY.
PRAGMA foreign_keys = ON;
CREATE TABLE lab_state (
 id INTEGER PRIMARY KEY CHECK(id=1),
 write_enabled INTEGER NOT NULL CHECK(write_enabled IN(0,1)),
 read_enabled INTEGER NOT NULL CHECK(read_enabled IN(0,1)),
 recovery_enabled INTEGER NOT NULL CHECK(recovery_enabled IN(0,1))
);
INSERT INTO lab_state VALUES(1,0,0,0);
CREATE TABLE lab_identities (
 subject TEXT PRIMARY KEY NOT NULL CHECK(length(subject)=64 AND subject NOT GLOB '*[^0-9a-f]*'),
 email_tag TEXT NOT NULL UNIQUE CHECK(length(email_tag)=64 AND email_tag NOT GLOB '*[^0-9a-f]*'),
 slot TEXT NOT NULL UNIQUE CHECK(slot IN('friend-a','friend-b')),
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN(0,1))
);
CREATE TRIGGER identity_no_delete BEFORE DELETE ON lab_identities BEGIN
 SELECT RAISE(ABORT,'immutable_identity');
END;
CREATE TRIGGER identity_no_rebind BEFORE UPDATE ON lab_identities
WHEN OLD.subject<>NEW.subject OR OLD.email_tag<>NEW.email_tag OR OLD.slot<>NEW.slot OR NEW.revoked<OLD.revoked
BEGIN SELECT RAISE(ABORT,'immutable_identity'); END;
CREATE TABLE lab_catalog (
 market TEXT NOT NULL, provider TEXT NOT NULL, ticker TEXT NOT NULL,
 product TEXT NOT NULL CHECK(product IN('SPOT','CFD','FUTURE','INDEX')),
 contract TEXT NOT NULL, source_group TEXT NOT NULL,
 active INTEGER NOT NULL CHECK(active IN(0,1)),
 PRIMARY KEY(market,provider,ticker,product,contract),
 CHECK((product='FUTURE' AND length(contract)>0 AND instr(contract,'!')=0 AND instr(ticker,'!')=0)
 OR (product<>'FUTURE' AND contract=''))
);
CREATE TABLE lab_entries (
 id INTEGER PRIMARY KEY,
 subject TEXT NOT NULL REFERENCES lab_identities(subject),
 request_id TEXT NOT NULL, market TEXT NOT NULL, provider TEXT NOT NULL, ticker TEXT NOT NULL,
 product TEXT NOT NULL, contract TEXT NOT NULL, period TEXT NOT NULL,
 kind TEXT NOT NULL, price TEXT NOT NULL, anchor_utc TEXT NOT NULL,
 observed_utc TEXT NOT NULL, received_utc TEXT NOT NULL, note TEXT NOT NULL,
 source_group TEXT NOT NULL,
 UNIQUE(subject,request_id),
 UNIQUE(subject,market,provider,ticker,product,contract,period,kind,price,anchor_utc),
 CHECK(period IN('DAY','WEEK','CURRENT_MONTH','PREVIOUS_MONTH')),
 CHECK(kind IN('DELTA_PEAK','EFFORT_RESULT','OTHER_VOLUME_LEVEL')),
 CHECK(length(note)<=280 AND length(request_id)=36 AND length(price)<=17),
 CHECK(length(anchor_utc)=20 AND length(observed_utc)=20 AND length(received_utc)=20),
 CHECK(anchor_utc<=observed_utc AND observed_utc<=received_utc),
 FOREIGN KEY(market,provider,ticker,product,contract)
 REFERENCES lab_catalog(market,provider,ticker,product,contract)
);
CREATE INDEX lab_entries_day ON lab_entries(subject,received_utc);
CREATE TRIGGER entry_guard BEFORE INSERT ON lab_entries BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND write_enabled=1)
 THEN RAISE(ABORT,'disabled') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_identities WHERE subject=NEW.subject AND revoked=0)
 THEN RAISE(ABORT,'identity_denied') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_catalog WHERE market=NEW.market AND provider=NEW.provider
 AND ticker=NEW.ticker AND product=NEW.product AND contract=NEW.contract
 AND source_group=NEW.source_group AND active=1) THEN RAISE(ABORT,'mapping_denied') END;
 SELECT CASE WHEN (SELECT count(*) FROM lab_entries)>=200 OR
 (SELECT count(*) FROM lab_entries WHERE subject=NEW.subject
 AND received_utc>=substr(NEW.received_utc,1,10)||'T00:00:00Z'
 AND received_utc<=substr(NEW.received_utc,1,10)||'T23:59:59Z')>=20
 THEN RAISE(ABORT,'capacity') END;
END;
CREATE TRIGGER entry_no_update BEFORE UPDATE ON lab_entries BEGIN
 SELECT RAISE(ABORT,'immutable_entry');
END;
CREATE TRIGGER entry_no_delete BEFORE DELETE ON lab_entries BEGIN
 SELECT RAISE(ABORT,'immutable_entry');
END;

-- Empty owner registry; explicit offline enrollment only, never from browser input.
CREATE TABLE lab_owner (
 id INTEGER PRIMARY KEY CHECK(id=1),
 subject TEXT NOT NULL UNIQUE CHECK(length(subject)=64 AND subject NOT GLOB '*[^0-9a-f]*'),
 email_tag TEXT NOT NULL UNIQUE CHECK(length(email_tag)=64 AND email_tag NOT GLOB '*[^0-9a-f]*'),
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN(0,1))
);
CREATE TRIGGER owner_no_delete BEFORE DELETE ON lab_owner BEGIN
 SELECT RAISE(ABORT,'immutable_owner');
END;
CREATE TRIGGER owner_no_rebind BEFORE UPDATE ON lab_owner
WHEN OLD.id<>NEW.id OR OLD.subject<>NEW.subject OR OLD.email_tag<>NEW.email_tag OR NEW.revoked<OLD.revoked
BEGIN SELECT RAISE(ABORT,'immutable_owner'); END;
CREATE TABLE lab_reviews (
 id INTEGER PRIMARY KEY,
 entry_id INTEGER NOT NULL REFERENCES lab_entries(id),
 owner TEXT NOT NULL REFERENCES lab_owner(subject),
 action TEXT NOT NULL CHECK(action IN('APPROVED','REJECTED','REVOKED')),
 at_utc TEXT NOT NULL CHECK(length(at_utc)=20 AND at_utc GLOB '????-??-??T??:??:??Z'),
 reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 280 AND length(reason)<=280),
 UNIQUE(entry_id,action)
);
CREATE INDEX lab_reviews_entry ON lab_reviews(entry_id,id);
CREATE TRIGGER review_guard BEFORE INSERT ON lab_reviews BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND ((NEW.action='REVOKED' AND recovery_enabled=1) OR (NEW.action<>'REVOKED' AND write_enabled=1)))
 THEN RAISE(ABORT,'disabled') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=NEW.owner AND revoked=0)
 THEN RAISE(ABORT,'owner_denied') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_entries WHERE id=NEW.entry_id AND received_utc<=NEW.at_utc)
 OR EXISTS(SELECT 1 FROM lab_reviews WHERE at_utc>NEW.at_utc)
 THEN RAISE(ABORT,'review_clock_or_entry') END;
 SELECT CASE WHEN NOT (
 (NEW.action IN('APPROVED','REJECTED') AND NOT EXISTS(SELECT 1 FROM lab_reviews WHERE entry_id=NEW.entry_id))
 OR (NEW.action='REVOKED' AND COALESCE((SELECT action FROM lab_reviews WHERE entry_id=NEW.entry_id ORDER BY id DESC LIMIT 1),'UNREVIEWED')='APPROVED')
 ) THEN RAISE(ABORT,'review_transition') END;
 SELECT CASE WHEN NEW.action='APPROVED' AND NOT EXISTS(
 SELECT 1 FROM lab_entries e JOIN lab_identities i ON i.subject=e.subject AND i.revoked=0
 JOIN lab_catalog m ON m.market=e.market AND m.provider=e.provider AND m.ticker=e.ticker
 AND m.product=e.product AND m.contract=e.contract AND m.source_group=e.source_group AND m.active=1
 WHERE e.id=NEW.entry_id) THEN RAISE(ABORT,'approval_source_denied') END;
END;
CREATE TRIGGER review_no_update BEFORE UPDATE ON lab_reviews BEGIN
 SELECT RAISE(ABORT,'immutable_review');
END;
CREATE TRIGGER review_no_delete BEFORE DELETE ON lab_reviews BEGIN
 SELECT RAISE(ABORT,'immutable_review');
END;

-- Cross-role separation; immutable subjects/slots and exact email tag.
CREATE TRIGGER identity_role_separation BEFORE INSERT ON lab_identities
WHEN EXISTS(SELECT 1 FROM lab_owner WHERE subject=NEW.subject OR email_tag=NEW.email_tag)
BEGIN SELECT RAISE(ABORT,'role_conflict'); END;
CREATE TRIGGER owner_role_separation BEFORE INSERT ON lab_owner
WHEN EXISTS(SELECT 1 FROM lab_identities WHERE subject=NEW.subject OR email_tag=NEW.email_tag)
BEGIN SELECT RAISE(ABORT,'role_conflict'); END;
-- Durable operator action; direct privileged SQL remains outside the app trust boundary.
CREATE TABLE lab_identity_revocations (
 subject TEXT PRIMARY KEY NOT NULL REFERENCES lab_identities(subject),
 owner TEXT NOT NULL REFERENCES lab_owner(subject),
 at_utc TEXT NOT NULL CHECK(length(at_utc)=20 AND at_utc GLOB '????-??-??T??:??:??Z')
);
CREATE TRIGGER identity_revocation_guard BEFORE INSERT ON lab_identity_revocations BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND recovery_enabled=1)
 OR NOT EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=NEW.owner AND revoked=0)
 OR NOT EXISTS(SELECT 1 FROM lab_identities WHERE subject=NEW.subject AND revoked=0)
 OR EXISTS(SELECT 1 FROM lab_entries WHERE subject=NEW.subject AND received_utc>NEW.at_utc)
 THEN RAISE(ABORT,'revocation_denied') END;
END;
CREATE TRIGGER identity_revocation_apply AFTER INSERT ON lab_identity_revocations BEGIN
 UPDATE lab_identities SET revoked=1 WHERE subject=NEW.subject;
END;
CREATE TRIGGER identity_revocation_no_update BEFORE UPDATE ON lab_identity_revocations BEGIN
 SELECT RAISE(ABORT,'immutable_revocation'); END;
CREATE TRIGGER identity_revocation_no_delete BEFORE DELETE ON lab_identity_revocations BEGIN
 SELECT RAISE(ABORT,'immutable_revocation'); END;
