-- REMURA Contributors v0.77 LAB — 21/11/2026 16:44 CET
-- Additive EMPTY SQLite/D1-compatible OWNER audit only. NEVER apply to cloud here.
-- Append-only independent ledger; original-level RESERVED locks MUST remain intact.
PRAGMA foreign_keys=ON;
CREATE TABLE lab_new_level_owner_audit_v077 (
 id INTEGER PRIMARY KEY,
 subject TEXT NOT NULL,
 request_id TEXT NOT NULL,
 owner_subject TEXT NOT NULL REFERENCES lab_owner(subject),
 classification TEXT NOT NULL CHECK(classification IN('RECEIPT_FOUND','RECEIPT_NOT_OBSERVED')),
 receipt_id INTEGER REFERENCES lab_entries(id),
 reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 280 AND length(reason)<=280),
 at_utc TEXT NOT NULL CHECK(length(at_utc)=20 AND at_utc GLOB '????-??-??T??:??:??Z'),
 FOREIGN KEY(subject,request_id) REFERENCES lab_new_level_attempts(subject,request_id),
 UNIQUE(subject,request_id,classification),
 CHECK((classification='RECEIPT_FOUND' AND receipt_id IS NOT NULL AND receipt_id>0) OR
       (classification='RECEIPT_NOT_OBSERVED' AND receipt_id IS NULL))
);
CREATE INDEX lab_owner_attempt_audit_history_v077
 ON lab_new_level_owner_audit_v077(subject,request_id,id);
CREATE TRIGGER lab_owner_attempt_audit_guard_v077 BEFORE INSERT ON lab_new_level_owner_audit_v077
BEGIN
 SELECT CASE WHEN NOT EXISTS(
  SELECT 1 FROM lab_owner o JOIN lab_state s ON s.id=1 JOIN lab_generation g ON g.id=1
  WHERE o.subject=NEW.owner_subject AND o.revoked=0 AND s.read_enabled=1 AND s.recovery_enabled=1
 ) THEN RAISE(ABORT,'owner_audit_access_denied') END;
 SELECT CASE WHEN NOT EXISTS(
  SELECT 1 FROM lab_new_level_attempts a WHERE a.subject=NEW.subject AND a.request_id=NEW.request_id
  AND a.state='RESERVED' AND NEW.at_utc>=a.claimed_utc
 ) THEN RAISE(ABORT,'owner_audit_not_unresolved') END;
 SELECT CASE WHEN
  (NEW.classification='RECEIPT_FOUND' AND NOT EXISTS(
   SELECT 1 FROM lab_entries e WHERE e.id=NEW.receipt_id AND e.subject=NEW.subject
   AND e.request_id=NEW.request_id AND e.received_utc<=NEW.at_utc))
  OR
  (NEW.classification='RECEIPT_NOT_OBSERVED' AND EXISTS(
   SELECT 1 FROM lab_entries e WHERE e.subject=NEW.subject AND e.request_id=NEW.request_id))
  THEN RAISE(ABORT,'owner_audit_evidence_conflict') END;
 SELECT CASE WHEN (SELECT count(*) FROM lab_new_level_owner_audit_v077)>=400
  THEN RAISE(ABORT,'owner_audit_capacity') END;
END;
CREATE TRIGGER lab_owner_attempt_audit_no_update_v077
 BEFORE UPDATE ON lab_new_level_owner_audit_v077 BEGIN
 SELECT RAISE(ABORT,'owner_audit_immutable');
END;
CREATE TRIGGER lab_owner_attempt_audit_no_delete_v077
 BEFORE DELETE ON lab_new_level_owner_audit_v077 BEGIN
 SELECT RAISE(ABORT,'owner_audit_immutable');
END;
-- RECEIPT_NOT_OBSERVED documents a snapshot ONLY, not proof of nonexistence.
-- Neither classification removes an attempt lock nor makes can_submit true.
-- No HTTP route may UPDATE/DELETE either lab_new_level_attempts or this audit.
