-- V30.19 LAB only; apply AFTER proposal-schema.sql in the same migration.
-- Never apply to real D1 without separate approval; install with Telegram OFF and writes closed.
CREATE TABLE lab_approval_policy_v3019(
 id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL CHECK(mode IN('AUTOMATIC','MANUAL')),
 revision INTEGER NOT NULL CHECK(revision>=1)
) STRICT;
INSERT INTO lab_approval_policy_v3019 VALUES(1,'AUTOMATIC',1);
CREATE TABLE lab_proposal_admission_v3019(
 proposal_id INTEGER PRIMARY KEY REFERENCES lab_proposals_v3019(id),
 mode TEXT NOT NULL CHECK(mode IN('AUTOMATIC','MANUAL')),
 revision INTEGER NOT NULL CHECK(revision>=1), epoch INTEGER CHECK(epoch>=1)
) STRICT;
CREATE TABLE lab_proposal_decision_v3019(
 proposal_id INTEGER PRIMARY KEY REFERENCES lab_proposals_v3019(id),
 action TEXT NOT NULL CHECK(action IN('APPROVED','REJECTED')),
 origin TEXT NOT NULL CHECK(origin IN('AUTOMATIC','OWNER')),
 actor_subject TEXT, actor_email_tag TEXT,
 reason TEXT NOT NULL CHECK(length(reason) BETWEEN 1 AND 280),
 decided_utc TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%SZ','now')),
 CHECK((origin='AUTOMATIC' AND action='APPROVED' AND actor_subject IS NULL AND actor_email_tag IS NULL)
 OR (origin='OWNER' AND actor_subject IS NOT NULL AND actor_email_tag IS NOT NULL))
) STRICT;
CREATE TABLE lab_policy_audit_v3019(
 id INTEGER PRIMARY KEY, setting TEXT NOT NULL CHECK(setting IN('APPROVAL','TELEGRAM')),
 old_value TEXT NOT NULL,new_value TEXT NOT NULL, revision INTEGER NOT NULL,
 actor_subject TEXT NOT NULL, actor_email_tag TEXT NOT NULL,
 changed_utc TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%SZ','now'))
) STRICT;
CREATE TRIGGER lab_approval_policy_guard_v3019 BEFORE UPDATE ON lab_approval_policy_v3019 BEGIN
 SELECT CASE WHEN NEW.id<>OLD.id OR NEW.mode=OLD.mode OR NEW.revision<>OLD.revision+1
 OR NOT EXISTS(SELECT 1 FROM lab_owner o CROSS JOIN lab_state s WHERE o.id=1 AND o.revoked=0 AND s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0)
 THEN RAISE(ABORT,'approval_policy_denied') END;
END;
CREATE TRIGGER lab_approval_policy_audit_v3019 AFTER UPDATE ON lab_approval_policy_v3019 BEGIN
 INSERT INTO lab_policy_audit_v3019(setting,old_value,new_value,revision,actor_subject,actor_email_tag)
 SELECT 'APPROVAL',OLD.mode,NEW.mode,NEW.revision,subject,email_tag FROM lab_owner WHERE id=1;
END;
CREATE TRIGGER lab_telegram_policy_audit_v3019 AFTER UPDATE ON lab_telegram_policy_v3012
 WHEN OLD.enabled<>NEW.enabled OR OLD.epoch<>NEW.epoch BEGIN
 INSERT INTO lab_policy_audit_v3019(setting,old_value,new_value,revision,actor_subject,actor_email_tag)
 SELECT 'TELEGRAM',CAST(OLD.enabled AS TEXT),CAST(NEW.enabled AS TEXT),NEW.epoch,subject,email_tag FROM lab_owner WHERE id=1;
END;
-- The earlier LAB enqueue-on-intake trigger must not coexist with decision-based enqueue.
DROP TRIGGER lab_proposal_enqueue_v3019;
CREATE TRIGGER lab_proposal_admit_v3019 AFTER INSERT ON lab_proposals_v3019 BEGIN
 INSERT INTO lab_proposal_admission_v3019(proposal_id,mode,revision,epoch)
 SELECT NEW.id,a.mode,a.revision,CASE WHEN NEW.publication_mode='TELEGRAM' AND p.enabled=1 AND EXISTS(
 SELECT 1 FROM lab_telegram_sources_v3012 m WHERE (m.market,m.provider,m.ticker,m.product,m.contract)=(NEW.market,NEW.provider,NEW.ticker,NEW.product,NEW.contract)) THEN p.epoch ELSE NULL END
 FROM lab_approval_policy_v3019 a CROSS JOIN lab_telegram_policy_v3012 p WHERE a.id=1 AND p.id=1;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_proposal_admission_v3019 WHERE proposal_id=NEW.id) THEN RAISE(ABORT,'admission_missing') END;
 INSERT INTO lab_proposal_decision_v3019(proposal_id,action,origin,reason)
 SELECT NEW.id,'APPROVED','AUTOMATIC','Automatic approval at intake' FROM lab_proposal_admission_v3019 WHERE proposal_id=NEW.id AND mode='AUTOMATIC';
END;
CREATE TRIGGER lab_proposal_decision_guard_v3019 BEFORE INSERT ON lab_proposal_decision_v3019 BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM lab_proposal_decision_v3019 WHERE proposal_id=NEW.proposal_id)
 OR NOT EXISTS(SELECT 1 FROM lab_proposal_admission_v3019 a WHERE a.proposal_id=NEW.proposal_id
 AND ((a.mode='AUTOMATIC' AND NEW.origin='AUTOMATIC') OR (a.mode='MANUAL' AND NEW.origin='OWNER')))
 OR NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=1 AND recovery_enabled=0)
 OR (NEW.origin='OWNER' AND NOT EXISTS(SELECT 1 FROM lab_owner o WHERE o.id=1 AND o.revoked=0 AND o.subject=NEW.actor_subject AND o.email_tag=NEW.actor_email_tag))
 THEN RAISE(ABORT,'decision_denied') END;
END;
CREATE TRIGGER lab_proposal_decision_enqueue_v3019 AFTER INSERT ON lab_proposal_decision_v3019 WHEN NEW.action='APPROVED' BEGIN
 INSERT INTO lab_proposal_outbox_v3019(proposal_id,epoch,state,queued_utc)
 SELECT e.id,p.epoch,'PENDING',NEW.decided_utc FROM lab_proposals_v3019 e
 JOIN lab_proposal_admission_v3019 a ON a.proposal_id=e.id
 JOIN lab_telegram_policy_v3012 p ON p.id=1 AND p.enabled=1 AND p.epoch=a.epoch
 JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag AND i.revoked=0 AND i.slot IN('friend-b','friend-c')
 JOIN lab_telegram_sources_v3012 m ON (m.market,m.provider,m.ticker,m.product,m.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
 JOIN lab_level_catalog_v110 c ON (c.market,c.provider,c.ticker,c.product,c.contract,c.source_group)=(e.market,e.provider,e.ticker,e.product,e.contract,e.source_group) AND c.active=1
 WHERE e.id=NEW.proposal_id AND e.publication_mode='TELEGRAM' AND e.provider<>'ECB';
END;
-- Rollback to V30.18 remains read-only for legacy intake; explicit review needed to reopen old writes.
CREATE TRIGGER lab_legacy_submit_closed_v3019 BEFORE INSERT ON lab_level_attempts_v110 BEGIN SELECT RAISE(ABORT,'batch_only'); END;
CREATE TRIGGER lab_admission_no_update_v3019 BEFORE UPDATE ON lab_proposal_admission_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_admission_no_delete_v3019 BEFORE DELETE ON lab_proposal_admission_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_admission_no_replace_v3019 BEFORE INSERT ON lab_proposal_admission_v3019 WHEN EXISTS(SELECT 1 FROM lab_proposal_admission_v3019 WHERE proposal_id=NEW.proposal_id) BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_decision_no_update_v3019 BEFORE UPDATE ON lab_proposal_decision_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_decision_no_delete_v3019 BEFORE DELETE ON lab_proposal_decision_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_approval_no_delete_v3019 BEFORE DELETE ON lab_approval_policy_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_approval_no_replace_v3019 BEFORE INSERT ON lab_approval_policy_v3019 WHEN EXISTS(SELECT 1 FROM lab_approval_policy_v3019) BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_policy_audit_no_update_v3019 BEFORE UPDATE ON lab_policy_audit_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_policy_audit_no_delete_v3019 BEFORE DELETE ON lab_policy_audit_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_policy_audit_no_replace_v3019 BEFORE INSERT ON lab_policy_audit_v3019 WHEN EXISTS(SELECT 1 FROM lab_policy_audit_v3019 WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'immutable'); END;
