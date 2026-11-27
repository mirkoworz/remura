-- REMURA v0.8.120 LAB — 17/11/2026 07:04 CET (session start)
-- Fresh isolated fixture only, after level_admission_candidate.sql and
-- level_receipt_candidate.sql (v1 receipt table remains unused). Never migrate.
CREATE TABLE level_permits_v2(
 attempt INTEGER PRIMARY KEY CHECK(attempt BETWEEN 1 AND 48),
 pin TEXT NOT NULL CHECK(length(pin)=64 AND pin NOT GLOB '*[^0-9a-f]*'),
 received_ms INTEGER NOT NULL CHECK(typeof(received_ms)='integer' AND received_ms BETWEEN 1 AND 4102444799999)
);
CREATE TRIGGER level_permits_capture_v2 AFTER UPDATE ON level_admission_v1
 WHEN NEW.enabled=1 AND NEW.allowed=1 AND NEW.attempts=OLD.attempts+1
 BEGIN INSERT INTO level_permits_v2 VALUES(NEW.attempts,NEW.pin,NEW.last_ms); END;
CREATE TABLE level_finalizations_v2(
 attempt INTEGER PRIMARY KEY REFERENCES level_permits_v2(attempt),
 completed_ms INTEGER NOT NULL CHECK(typeof(completed_ms)='integer' AND completed_ms BETWEEN 1 AND 4102444799999),
 outcome TEXT NOT NULL CHECK(outcome IN ('STORED_SYNTHETIC','DUPLICATE','CONFLICT','CAPACITY_OR_ORDER')),
 close_ms INTEGER NOT NULL CHECK(typeof(close_ms)='integer' AND close_ms>0 AND close_ms<4102444800000 AND close_ms%300000=0),
 received_ms INTEGER NOT NULL CHECK(typeof(received_ms)='integer' AND received_ms BETWEEN close_ms AND close_ms+120000),
 sender_ms INTEGER NOT NULL CHECK(typeof(sender_ms)='integer' AND sender_ms BETWEEN close_ms AND received_ms),
 digest TEXT NOT NULL CHECK(length(digest)=64 AND digest NOT GLOB '*[^0-9a-f]*'),
 body TEXT,
 present_levels INTEGER NOT NULL CHECK(typeof(present_levels)='integer' AND present_levels BETWEEN 0 AND 6),
 CHECK((outcome='STORED_SYNTHETIC' AND typeof(body)='text' AND length(CAST(body AS BLOB)) BETWEEN 1 AND 15000)
 OR (outcome<>'STORED_SYNTHETIC' AND body IS NULL))
);
CREATE UNIQUE INDEX level_first_close_v2 ON level_finalizations_v2(close_ms) WHERE outcome='STORED_SYNTHETIC';
CREATE VIEW level_receipts_v2 AS SELECT close_ms,received_ms AS first_received_ms,sender_ms,attempt,digest AS body_digest,body,present_levels
 FROM level_finalizations_v2 WHERE outcome='STORED_SYNTHETIC';
CREATE TRIGGER level_permits_no_update_v2 BEFORE UPDATE ON level_permits_v2 BEGIN SELECT RAISE(ABORT,'immutable_permit'); END;
CREATE TRIGGER level_permits_no_delete_v2 BEFORE DELETE ON level_permits_v2 BEGIN SELECT RAISE(ABORT,'immutable_permit'); END;
CREATE TRIGGER level_finalizations_no_update_v2 BEFORE UPDATE ON level_finalizations_v2 BEGIN SELECT RAISE(ABORT,'immutable_finalization'); END;
CREATE TRIGGER level_finalizations_no_delete_v2 BEFORE DELETE ON level_finalizations_v2 BEGIN SELECT RAISE(ABORT,'immutable_finalization'); END;
CREATE TRIGGER level_finalizations_guard_v2 BEFORE INSERT ON level_finalizations_v2 BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM level_permits_v2 p JOIN level_admission_v1 a ON a.id=1 AND a.pin=p.pin
 JOIN level_receipt_session_v1 s ON s.id=a.id AND s.pin=a.pin
 WHERE p.attempt=NEW.attempt AND p.received_ms=NEW.received_ms AND a.enabled=1
 AND NEW.completed_ms BETWEEN p.received_ms AND p.received_ms+5000 AND NEW.close_ms>s.cutoff_ms)
 THEN RAISE(ABORT,'closed_or_expired') END;
 SELECT CASE WHEN NEW.outcome<>CASE
 WHEN EXISTS(SELECT 1 FROM level_receipts_v2 WHERE close_ms=NEW.close_ms AND body_digest=NEW.digest) THEN 'DUPLICATE'
 WHEN EXISTS(SELECT 1 FROM level_receipts_v2 WHERE close_ms=NEW.close_ms) THEN 'CONFLICT'
 WHEN (SELECT count(*) FROM level_receipts_v2)>=12 OR EXISTS(SELECT 1 FROM level_receipts_v2 WHERE close_ms>=NEW.close_ms OR first_received_ms>NEW.received_ms) THEN 'CAPACITY_OR_ORDER'
 ELSE 'STORED_SYNTHETIC' END THEN RAISE(ABORT,'invalid_outcome') END;
END;
