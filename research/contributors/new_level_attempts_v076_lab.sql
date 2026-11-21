-- REMURA Contributors v0.76 LAB — 21/11/2026 15:57 CET (Europe/Rome)
-- ADDITIVE EMPTY CANDIDATE ONLY; apply solely to synthetic fixture, NOT Cloudflare D1.
-- New original-level intake attempts are DISTINCT from amendment reservations/journals.
-- The unique partial index is the cross-tab, cross-device and restart safety barrier.
PRAGMA foreign_keys=ON;
CREATE TABLE lab_new_level_attempts (
 subject TEXT NOT NULL REFERENCES lab_identities(subject),
 email_tag TEXT NOT NULL,
 request_id TEXT NOT NULL CHECK(length(request_id)=36),
 fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64 AND fingerprint NOT GLOB '*[^0-9a-f]*'),
 state TEXT NOT NULL CHECK(state IN ('RESERVED','COMMITTED')),
 receipt_id INTEGER REFERENCES lab_entries(id),
 claimed_utc TEXT NOT NULL CHECK(length(claimed_utc)=20 AND claimed_utc GLOB '????-??-??T??:??:??Z'),
 confirmed_utc TEXT,
 PRIMARY KEY(subject,request_id),
 CHECK ((state='RESERVED' AND receipt_id IS NULL AND confirmed_utc IS NULL) OR
        (state='COMMITTED' AND receipt_id IS NOT NULL AND confirmed_utc IS NOT NULL))
);
CREATE UNIQUE INDEX new_level_single_inflight
 ON lab_new_level_attempts(subject) WHERE state='RESERVED';
CREATE INDEX new_level_recent ON lab_new_level_attempts(subject,claimed_utc DESC);
CREATE TRIGGER new_level_no_delete BEFORE DELETE ON lab_new_level_attempts BEGIN
 SELECT RAISE(ABORT,'new_level_attempt_immutable');
END;
CREATE TRIGGER new_level_guard_update BEFORE UPDATE ON lab_new_level_attempts
WHEN OLD.subject<>NEW.subject OR OLD.email_tag<>NEW.email_tag OR
 OLD.request_id<>NEW.request_id OR OLD.fingerprint<>NEW.fingerprint OR
 OLD.claimed_utc<>NEW.claimed_utc OR OLD.state<>'RESERVED' OR NEW.state<>'COMMITTED' OR
 NEW.receipt_id IS NULL OR NEW.confirmed_utc IS NULL OR
 NOT EXISTS(SELECT 1 FROM lab_entries e
 WHERE e.id=NEW.receipt_id AND e.subject=NEW.subject AND e.request_id=NEW.request_id)
BEGIN SELECT RAISE(ABORT,'new_level_attempt_transition_denied'); END;
-- No UPDATE to CLOSED/RETRY states exists. RESERVED without a confirmed receipt
-- is MANUAL OWNER RECOVERY ONLY, never permission for an automatic retry.
