-- REMURA Contributors v0.64 LAB — 21/11/2026 CET.
-- ADDITIVE to verified d1_access_candidate.sql + d1_amendment_v059_lab.sql.
-- STRICTLY offline fixture; never applied to Cloudflare.
PRAGMA foreign_keys=ON;
CREATE TABLE lab_amend_attempts_v064 (
 id INTEGER PRIMARY KEY,
 subject TEXT NOT NULL REFERENCES lab_identities(subject),
 request_id TEXT NOT NULL CHECK(length(request_id)=36),
 source_entry_id INTEGER NOT NULL REFERENCES lab_entries(id),
 price TEXT NOT NULL CHECK(length(price) BETWEEN 1 AND 17),
 observed_utc TEXT NOT NULL CHECK(length(observed_utc)=20),
 note TEXT NOT NULL CHECK(length(note)<=280),
 reserved_utc TEXT NOT NULL CHECK(length(reserved_utc)=20),
 UNIQUE(subject,request_id)
);
CREATE INDEX lab_attempt_subject_v064 ON lab_amend_attempts_v064(subject,id);
CREATE TABLE lab_amend_releases_v064 (
 attempt_id INTEGER PRIMARY KEY REFERENCES lab_amend_attempts_v064(id),
 owner TEXT NOT NULL REFERENCES lab_owner(subject),
 disposition TEXT NOT NULL CHECK(disposition IN('REVIEWED','ABORTED_BY_OWNER')),
 reason TEXT NOT NULL CHECK(length(trim(reason)) BETWEEN 1 AND 280),
 released_utc TEXT NOT NULL CHECK(length(released_utc)=20)
);
CREATE TRIGGER lab_attempt_guard_v064 BEFORE INSERT ON lab_amend_attempts_v064 BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND write_enabled=1)
 OR NOT EXISTS(SELECT 1 FROM lab_identities WHERE subject=NEW.subject AND revoked=0)
 OR NOT EXISTS(SELECT 1 FROM lab_entries e WHERE e.id=NEW.source_entry_id AND e.subject=NEW.subject
  AND (SELECT action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1)='APPROVED')
 THEN RAISE(ABORT,'attempt_actor_or_source_denied') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM lab_amend_attempts_v064 a WHERE a.subject=NEW.subject
  AND NOT EXISTS(SELECT 1 FROM lab_amend_releases_v064 r WHERE r.attempt_id=a.id))
 THEN RAISE(ABORT,'attempt_unresolved') END;
 SELECT CASE WHEN NEW.reserved_utc<COALESCE((SELECT max(reserved_utc) FROM lab_amend_attempts_v064 WHERE subject=NEW.subject),'0000')
 OR (SELECT count(*) FROM lab_amend_attempts_v064)>=200
 THEN RAISE(ABORT,'attempt_clock_or_capacity') END;
END;
CREATE TRIGGER lab_attempt_immutable_up_v064 BEFORE UPDATE ON lab_amend_attempts_v064 BEGIN SELECT RAISE(ABORT,'immutable_attempt'); END;
CREATE TRIGGER lab_attempt_immutable_del_v064 BEFORE DELETE ON lab_amend_attempts_v064 BEGIN SELECT RAISE(ABORT,'immutable_attempt'); END;

-- This mandatory guard prevents bypassing the reservation through the old v0.59 INSERT.
-- Even after a manual release, a DELAYED write using the former request is rejected.
CREATE TRIGGER lab_amend_requires_attempt_v064 BEFORE INSERT ON lab_level_amendments_v059 BEGIN
 SELECT CASE WHEN NOT EXISTS(
  SELECT 1 FROM lab_amend_attempts_v064 a WHERE a.subject=NEW.subject AND a.request_id=NEW.request_id
   AND a.source_entry_id=NEW.source_entry_id AND a.price=NEW.price AND a.observed_utc=NEW.observed_utc AND a.note=NEW.note
   AND a.reserved_utc<=NEW.received_utc
   AND NOT EXISTS(SELECT 1 FROM lab_amend_releases_v064 r WHERE r.attempt_id=a.id)
 ) THEN RAISE(ABORT,'reservation_required') END;
END;

CREATE TRIGGER lab_release_guard_v064 BEFORE INSERT ON lab_amend_releases_v064 BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND recovery_enabled=1)
  OR NOT EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=NEW.owner AND revoked=0)
  OR NOT EXISTS(SELECT 1 FROM lab_amend_attempts_v064 a WHERE a.id=NEW.attempt_id AND a.reserved_utc<=NEW.released_utc)
 THEN RAISE(ABORT,'release_owner_denied') END;
 SELECT CASE WHEN NEW.disposition='REVIEWED' AND NOT EXISTS(
  SELECT 1 FROM lab_amend_attempts_v064 a JOIN lab_level_amendments_v059 e
   ON e.subject=a.subject AND e.request_id=a.request_id AND e.source_entry_id=a.source_entry_id
  WHERE a.id=NEW.attempt_id AND
   (SELECT action FROM lab_level_amendment_reviews_v059 r WHERE r.amendment_id=e.id ORDER BY r.id DESC LIMIT 1)
    IN('APPROVED','REJECTED','REVOKED'))
 THEN RAISE(ABORT,'unreviewed_attempt') END;
 SELECT CASE WHEN NEW.disposition='ABORTED_BY_OWNER' AND EXISTS(
  SELECT 1 FROM lab_amend_attempts_v064 a JOIN lab_level_amendments_v059 e
   ON e.subject=a.subject AND e.request_id=a.request_id WHERE a.id=NEW.attempt_id)
 THEN RAISE(ABORT,'committed_cannot_abort') END;
END;
CREATE TRIGGER lab_release_immutable_up_v064 BEFORE UPDATE ON lab_amend_releases_v064 BEGIN SELECT RAISE(ABORT,'immutable_release'); END;
CREATE TRIGGER lab_release_immutable_del_v064 BEFORE DELETE ON lab_amend_releases_v064 BEGIN SELECT RAISE(ABORT,'immutable_release'); END;
