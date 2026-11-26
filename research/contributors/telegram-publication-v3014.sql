-- REMURA V30.14 LAB, after V30.12. Atomic migration, staging only.
-- Old clients, historical levels and unspecified choices remain PRIVATE.
ALTER TABLE lab_level_attempts_v110 ADD COLUMN publication_mode TEXT NOT NULL DEFAULT 'PRIVATE'
 CHECK(publication_mode IN ('PRIVATE','TEST','TELEGRAM'));
DROP TRIGGER lab_telegram_enqueue_v3012;
CREATE TRIGGER lab_telegram_enqueue_v3012 AFTER INSERT ON lab_level_attempts_v110
 WHEN NEW.publication_mode='TELEGRAM' AND NEW.duplicate_of IS NULL AND NEW.provider<>'ECB'
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

