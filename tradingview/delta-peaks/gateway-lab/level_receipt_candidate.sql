-- REMURA v0.8.118 LAB — 17/11/2026 CET
-- NEW separate fixture DB only, after level_admission_candidate.sql.
-- No initial rows, activation or migration.
CREATE TABLE level_receipt_session_v1(
 id INTEGER PRIMARY KEY CHECK(id=1),
 pin TEXT NOT NULL CHECK(length(pin)=64 AND pin NOT GLOB '*[^0-9a-f]*'),
 config_digest TEXT NOT NULL CHECK(length(config_digest)=64 AND config_digest NOT GLOB '*[^0-9a-f]*'),
 chart_type TEXT NOT NULL CHECK(length(chart_type) BETWEEN 1 AND 100),
 timezone TEXT NOT NULL CHECK(length(timezone) BETWEEN 1 AND 100),
 session_name TEXT NOT NULL CHECK(length(session_name) BETWEEN 1 AND 100),
 cutoff_ms INTEGER NOT NULL CHECK(typeof(cutoff_ms)='integer' AND cutoff_ms>0 AND cutoff_ms<4102444800000 AND cutoff_ms%300000=0)
);
CREATE TABLE level_receipts_v1(
 close_ms INTEGER PRIMARY KEY CHECK(close_ms>0 AND close_ms<4102444800000 AND close_ms%300000=0),
 first_received_ms INTEGER NOT NULL CHECK(typeof(first_received_ms)='integer' AND first_received_ms<4102444800000 AND first_received_ms BETWEEN close_ms AND close_ms+120000),
 sender_ms INTEGER NOT NULL CHECK(typeof(sender_ms)='integer' AND sender_ms BETWEEN close_ms AND first_received_ms),
 attempt INTEGER NOT NULL UNIQUE CHECK(typeof(attempt)='integer' AND attempt BETWEEN 1 AND 48),
 body_digest TEXT NOT NULL CHECK(length(body_digest)=64 AND body_digest NOT GLOB '*[^0-9a-f]*'),
 body TEXT NOT NULL CHECK(typeof(body)='text' AND length(CAST(body AS BLOB)) BETWEEN 1 AND 15000),
 present_levels INTEGER NOT NULL CHECK(typeof(present_levels)='integer' AND present_levels BETWEEN 0 AND 6)
);
CREATE TRIGGER level_receipt_session_no_update BEFORE UPDATE ON level_receipt_session_v1 BEGIN SELECT RAISE(ABORT,'immutable_session'); END;
CREATE TRIGGER level_receipt_session_no_delete BEFORE DELETE ON level_receipt_session_v1 BEGIN SELECT RAISE(ABORT,'immutable_session'); END;
CREATE TRIGGER level_receipts_no_update BEFORE UPDATE ON level_receipts_v1 BEGIN SELECT RAISE(ABORT,'immutable_receipt'); END;
CREATE TRIGGER level_receipts_no_delete BEFORE DELETE ON level_receipts_v1 BEGIN SELECT RAISE(ABORT,'immutable_receipt'); END;
-- Enforce core invariants even for accidental direct INSERT; not protection
-- from a privileged DB administrator or rollback to an old database.
CREATE TRIGGER level_receipts_insert_guard BEFORE INSERT ON level_receipts_v1 BEGIN
 SELECT CASE WHEN NOT EXISTS(
 SELECT 1 FROM level_admission_v1 a JOIN level_receipt_session_v1 s ON s.id=a.id AND s.pin=a.pin
 WHERE a.id=1 AND a.enabled=1 AND a.allowed=1 AND a.attempts=NEW.attempt AND a.last_ms<=NEW.first_received_ms AND NEW.close_ms>s.cutoff_ms
 ) THEN RAISE(ABORT,'closed_or_stale_reservation') END;
 SELECT CASE WHEN (SELECT count(*) FROM level_receipts_v1)>=12
 OR EXISTS(SELECT 1 FROM level_receipts_v1 WHERE close_ms>=NEW.close_ms OR first_received_ms>NEW.first_received_ms)
 THEN RAISE(ABORT,'capacity_or_order') END;
END;
