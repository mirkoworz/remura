-- REMURA V30.12 LAB - additive candidate, never run automatically.
-- Install in a single migration transaction, with staging writes closed.
CREATE TABLE lab_telegram_policy_v3012 (
 id INTEGER PRIMARY KEY CHECK(id=1),
 enabled INTEGER NOT NULL CHECK(enabled IN(0,1)),
 epoch INTEGER NOT NULL CHECK(epoch>=1),
 start_after_receipt INTEGER NOT NULL CHECK(start_after_receipt>=0)
) STRICT;
INSERT INTO lab_telegram_policy_v3012
 SELECT 1,0,1,COALESCE(MAX(id),0) FROM lab_level_attempts_v110;
CREATE TABLE lab_telegram_sources_v3012 (
 market TEXT NOT NULL, provider TEXT NOT NULL CHECK(provider<>'ECB'),
 ticker TEXT NOT NULL, product TEXT NOT NULL, contract TEXT NOT NULL,
 PRIMARY KEY(market,provider,ticker,product,contract),
 FOREIGN KEY(market,provider,ticker,product,contract)
 REFERENCES lab_level_catalog_v110(market,provider,ticker,product,contract)
) STRICT;
CREATE TABLE lab_telegram_outbox_v3012 (
 receipt_id INTEGER PRIMARY KEY REFERENCES lab_level_attempts_v110(id),
 epoch INTEGER NOT NULL CHECK(epoch>=1),
 state TEXT NOT NULL CHECK(state IN('PENDING','SENDING','SENT','UNKNOWN','BLOCKED')),
 queued_utc TEXT NOT NULL,
 claimed_utc TEXT,
 finished_utc TEXT,
 telegram_message_id INTEGER,
 CHECK((state='PENDING' AND claimed_utc IS NULL AND finished_utc IS NULL AND telegram_message_id IS NULL)
 OR (state='SENDING' AND claimed_utc IS NOT NULL AND finished_utc IS NULL AND telegram_message_id IS NULL)
 OR (state='SENT' AND claimed_utc IS NOT NULL AND finished_utc IS NOT NULL AND telegram_message_id>0 AND telegram_message_id IS NOT NULL)
 OR (state IN('UNKNOWN','BLOCKED') AND claimed_utc IS NOT NULL AND finished_utc IS NOT NULL AND telegram_message_id IS NULL))
) STRICT;
CREATE INDEX lab_telegram_pending_v3012 ON lab_telegram_outbox_v3012(epoch,receipt_id) WHERE state='PENDING';
CREATE TRIGGER lab_telegram_policy_guard_v3012 BEFORE UPDATE ON lab_telegram_policy_v3012 BEGIN
 SELECT CASE WHEN NEW.id<>OLD.id OR NEW.epoch<OLD.epoch OR NEW.start_after_receipt<OLD.start_after_receipt
 OR (NEW.enabled=1 AND OLD.enabled=0 AND
 (NEW.epoch<=OLD.epoch OR NEW.start_after_receipt<(SELECT COALESCE(MAX(id),0) FROM lab_level_attempts_v110)))
 OR (NEW.enabled=1 AND OLD.enabled=1 AND NEW.epoch<>OLD.epoch)
 THEN RAISE(ABORT,'telegram_policy_invalid') END;
END;
CREATE TRIGGER lab_telegram_outbox_transition_v3012 BEFORE UPDATE ON lab_telegram_outbox_v3012 BEGIN
 SELECT CASE WHEN NEW.receipt_id<>OLD.receipt_id OR NEW.epoch<>OLD.epoch OR NEW.queued_utc<>OLD.queued_utc
 OR NOT ((OLD.state='PENDING' AND NEW.state='SENDING') OR
 (OLD.state='SENDING' AND NEW.state IN('SENT','UNKNOWN','BLOCKED') AND NEW.claimed_utc=OLD.claimed_utc))
 THEN RAISE(ABORT,'telegram_transition_invalid') END;
END;
CREATE TRIGGER lab_telegram_outbox_no_delete_v3012 BEFORE DELETE ON lab_telegram_outbox_v3012
 BEGIN SELECT RAISE(ABORT,'telegram_outbox_immutable'); END;
-- Atomic with original receipt intake; no historic backfill, no new row for a duplicate.
CREATE TRIGGER lab_telegram_enqueue_v3012 AFTER INSERT ON lab_level_attempts_v110
 WHEN NEW.duplicate_of IS NULL AND NEW.provider<>'ECB'
 AND instr(upper(NEW.note),'TEST')=0 AND instr(upper(NEW.note),'COLLAUDO')=0
 AND instr(upper(NEW.note),'NON OPERATIVO')=0 AND instr(upper(NEW.note),'NON-OPERATIVO')=0
 BEGIN
 INSERT INTO lab_telegram_outbox_v3012(receipt_id,epoch,state,queued_utc)
 SELECT NEW.id,p.epoch,'PENDING',NEW.received_utc
 FROM lab_telegram_policy_v3012 p
 JOIN lab_identities i ON i.subject=NEW.subject AND i.email_tag=NEW.email_tag AND i.revoked=0
 JOIN lab_telegram_sources_v3012 m
 ON (m.market,m.provider,m.ticker,m.product,m.contract)=(NEW.market,NEW.provider,NEW.ticker,NEW.product,NEW.contract)
 WHERE p.id=1 AND p.enabled=1 AND NEW.id>p.start_after_receipt AND i.slot IN('friend-b','friend-c');
 END;
