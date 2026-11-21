-- REMURA Contributors v0.59 LAB -- 2026-11-21 CET
-- ADDITIVE SQL-only candidate for the EXISTING d1_access_candidate.sql layout.
-- No ALTER of lab_entries/lab_reviews, no binding, migration, deploy or identity enrollment.
-- Execute only on a disposable SQLite fixture after the original candidate schema.
PRAGMA foreign_keys=ON;

CREATE TABLE lab_level_amendments_v059 (
 id INTEGER PRIMARY KEY,
 subject TEXT NOT NULL REFERENCES lab_identities(subject),
 source_entry_id INTEGER NOT NULL REFERENCES lab_entries(id),
 request_id TEXT NOT NULL CHECK(length(request_id)=36),
 price TEXT NOT NULL CHECK(length(price) BETWEEN 1 AND 17),
 observed_utc TEXT NOT NULL CHECK(length(observed_utc)=20 AND observed_utc GLOB '????-??-??T??:??:??Z'),
 received_utc TEXT NOT NULL CHECK(length(received_utc)=20 AND received_utc GLOB '????-??-??T??:??:??Z'),
 note TEXT NOT NULL CHECK(length(note)<=280),
 UNIQUE(subject,request_id),
 CHECK(observed_utc<=received_utc)
);
CREATE INDEX lab_amendments_by_subject_v059 ON lab_level_amendments_v059(subject,id);
CREATE INDEX lab_amendments_by_source_v059 ON lab_level_amendments_v059(source_entry_id,id);

CREATE TRIGGER lab_amendment_insert_guard_v059 BEFORE INSERT ON lab_level_amendments_v059 BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND write_enabled=1)
 THEN RAISE(ABORT,'amend_closed') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_identities
   WHERE subject=NEW.subject AND revoked=0)
 THEN RAISE(ABORT,'amend_actor_denied') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_entries e JOIN lab_catalog m
    ON (m.market,m.provider,m.ticker,m.product,m.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
   WHERE e.id=NEW.source_entry_id AND e.subject=NEW.subject
    AND m.source_group=e.source_group AND m.active=1
    AND e.anchor_utc<=NEW.observed_utc AND e.received_utc<=NEW.received_utc
    AND (SELECT action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1)='APPROVED')
 THEN RAISE(ABORT,'amend_source_denied') END;
 SELECT CASE WHEN NEW.price NOT GLOB '*[1-9]*'
   OR NEW.price GLOB '*[^0-9.]*'
   OR length(NEW.price)-length(replace(NEW.price,'.',''))>1
   OR NEW.price LIKE '.%' OR NEW.price LIKE '%.'
   OR NEW.note GLOB '*['||char(1)||'-'||char(31)||']*'
 THEN RAISE(ABORT,'amend_payload_denied') END;
 SELECT CASE WHEN (SELECT count(*) FROM lab_level_amendments_v059)>=100
 OR (SELECT count(*) FROM lab_level_amendments_v059
     WHERE subject=NEW.subject AND received_utc>=substr(NEW.received_utc,1,10)||'T00:00:00Z'
     AND received_utc<=substr(NEW.received_utc,1,10)||'T23:59:59Z')>=10
 THEN RAISE(ABORT,'amend_capacity') END;
END;
CREATE TRIGGER lab_amendment_no_update_v059 BEFORE UPDATE ON lab_level_amendments_v059 BEGIN
 SELECT RAISE(ABORT,'immutable_amendment'); END;
CREATE TRIGGER lab_amendment_no_delete_v059 BEFORE DELETE ON lab_level_amendments_v059 BEGIN
 SELECT RAISE(ABORT,'immutable_amendment'); END;

CREATE TABLE lab_level_amendment_reviews_v059 (
 id INTEGER PRIMARY KEY,
 amendment_id INTEGER NOT NULL REFERENCES lab_level_amendments_v059(id),
 owner TEXT NOT NULL REFERENCES lab_owner(subject),
 action TEXT NOT NULL CHECK(action IN('APPROVED','REJECTED','REVOKED')),
 at_utc TEXT NOT NULL CHECK(length(at_utc)=20 AND at_utc GLOB '????-??-??T??:??:??Z'),
 reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 280),
 UNIQUE(amendment_id,action)
);
CREATE INDEX lab_amend_review_by_amendment_v059 ON lab_level_amendment_reviews_v059(amendment_id,id);
CREATE TRIGGER lab_amend_review_guard_v059 BEFORE INSERT ON lab_level_amendment_reviews_v059 BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND
   CASE WHEN NEW.action='REVOKED' THEN recovery_enabled=1 ELSE write_enabled=1 END)
 THEN RAISE(ABORT,'amend_review_closed') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=NEW.owner AND revoked=0)
 THEN RAISE(ABORT,'amend_owner_denied') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_level_amendments_v059 WHERE id=NEW.amendment_id AND received_utc<=NEW.at_utc)
 OR EXISTS(SELECT 1 FROM lab_level_amendment_reviews_v059 WHERE at_utc>NEW.at_utc)
 THEN RAISE(ABORT,'amend_review_clock') END;
 SELECT CASE WHEN NOT (
   (NEW.action IN('APPROVED','REJECTED') AND NOT EXISTS(SELECT 1 FROM lab_level_amendment_reviews_v059 WHERE amendment_id=NEW.amendment_id))
   OR (NEW.action='REVOKED' AND COALESCE((SELECT action FROM lab_level_amendment_reviews_v059
       WHERE amendment_id=NEW.amendment_id ORDER BY id DESC LIMIT 1),'UNREVIEWED')='APPROVED'))
 THEN RAISE(ABORT,'amend_review_transition') END;
 SELECT CASE WHEN NEW.action='APPROVED' AND NOT EXISTS(
   SELECT 1 FROM lab_level_amendments_v059 a JOIN lab_entries e ON e.id=a.source_entry_id
   JOIN lab_identities i ON i.subject=a.subject AND i.revoked=0
   JOIN lab_catalog m ON (m.market,m.provider,m.ticker,m.product,m.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
   WHERE a.id=NEW.amendment_id AND e.subject=a.subject AND m.source_group=e.source_group AND m.active=1
     AND (SELECT action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1)='APPROVED'
 ) THEN RAISE(ABORT,'amend_review_source_denied') END;
 SELECT CASE WHEN NEW.action='APPROVED' AND EXISTS(
   SELECT 1 FROM lab_level_amendments_v059 a
   JOIN lab_level_amendments_v059 prior ON prior.source_entry_id=a.source_entry_id AND prior.id<>a.id
   WHERE a.id=NEW.amendment_id
     AND (SELECT action FROM lab_level_amendment_reviews_v059 r WHERE r.amendment_id=prior.id ORDER BY r.id DESC LIMIT 1)='APPROVED'
 ) THEN RAISE(ABORT,'amend_already_approved') END;
END;
CREATE TRIGGER lab_amend_review_no_update_v059 BEFORE UPDATE ON lab_level_amendment_reviews_v059 BEGIN
 SELECT RAISE(ABORT,'immutable_amendment_review'); END;
CREATE TRIGGER lab_amend_review_no_delete_v059 BEFORE DELETE ON lab_level_amendment_reviews_v059 BEGIN
 SELECT RAISE(ABORT,'immutable_amendment_review'); END;

-- SQL for future trusted adapter ONLY: filter by server-verified subject+email_tag.
-- Return amended values ONLY when the source and most recent amendment are approved.
-- No public VIEW is deliberately created: the caller must enforce an ACL and subject scope.
