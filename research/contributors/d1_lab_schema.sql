-- REMURA Contributors v0.16 LAB — 14/11/2026 23:56 CET
-- SYNTHETIC ONLY: NOT a migration for any existing database; no deployment.
PRAGMA foreign_keys = ON;
CREATE TABLE lab_state (
 id INTEGER PRIMARY KEY CHECK(id=1),
 enabled INTEGER NOT NULL CHECK(enabled IN(0,1))
);
INSERT INTO lab_state VALUES(1,0);
CREATE TABLE lab_identities (
 subject TEXT PRIMARY KEY CHECK(length(subject) BETWEEN 1 AND 64),
 slot TEXT NOT NULL UNIQUE CHECK(slot IN('friend-a','friend-b')),
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN(0,1))
);
CREATE TRIGGER identity_no_delete BEFORE DELETE ON lab_identities BEGIN
 SELECT RAISE(ABORT,'immutable_identity');
END;
CREATE TRIGGER identity_no_rebind BEFORE UPDATE ON lab_identities
WHEN OLD.subject<>NEW.subject OR OLD.slot<>NEW.slot OR NEW.revoked<OLD.revoked
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
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1)
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
