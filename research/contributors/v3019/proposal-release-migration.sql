-- SOURCE proposal-preflight.sql git blob 94fee7629188286d345b1f3d67679e673bba51db
-- V30.19 LAB preflight; execute ONLY in same atomic transaction as both migrations.
CREATE TABLE lab_migration_guard_v3019(ok INTEGER NOT NULL CHECK(ok=1)) STRICT;
INSERT INTO lab_migration_guard_v3019
SELECT CASE WHEN
 (SELECT COUNT(*) FROM lab_state)=1 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=0 AND recovery_enabled=0)
 AND (SELECT COUNT(*) FROM lab_telegram_policy_v3012)=1
 AND EXISTS(SELECT 1 FROM lab_telegram_policy_v3012 WHERE id=1 AND enabled=0)
 AND NOT EXISTS(SELECT 1 FROM lab_telegram_outbox_v3012 WHERE state IN('PENDING','SENDING'))
 AND EXISTS(SELECT 1 FROM pragma_table_info('lab_level_attempts_v110') WHERE name='publication_mode')
 AND NOT EXISTS(SELECT 1 FROM sqlite_schema WHERE name IN('lab_proposals_v3019','lab_approval_policy_v3019','lab_proposal_outbox_v3019'))
 THEN 1 ELSE 0 END;
DROP TABLE lab_migration_guard_v3019;

-- SOURCE proposal-schema.sql git blob e5117086aaf802bde8117453b76f17f3d3c54c9d
-- V30.19 LAB candidate only. No automatic migration. Existing tables/triggers untouched.
CREATE TABLE lab_proposals_v3019 (
 id INTEGER PRIMARY KEY CHECK(id>0),
 subject TEXT NOT NULL REFERENCES lab_identities(subject),
 email_tag TEXT NOT NULL,
 request_id TEXT NOT NULL CHECK(length(request_id)=36),
 mapping_id TEXT NOT NULL,
 market TEXT NOT NULL, provider TEXT NOT NULL,ticker TEXT NOT NULL,product TEXT NOT NULL,contract TEXT NOT NULL,
 source_group TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN('DELTA_PEAK','EFFORT_RESULT','CVD_DIVERGENCE')),
 period TEXT NOT NULL CHECK(period IN('DAY','WEEK','CURRENT_MONTH','PREVIOUS_MONTH')),
 prices_json TEXT NOT NULL CHECK(json_valid(prices_json) AND json_type(prices_json)='array' AND json_array_length(prices_json) BETWEEN 1 AND 20),
 note TEXT NOT NULL CHECK(length(note)<=280),
 payload TEXT NOT NULL CHECK(json_valid(payload)),
 received_utc TEXT NOT NULL CHECK(length(received_utc)=20 AND received_utc GLOB '????-??-??T??:??:??Z'),
 publication_mode TEXT NOT NULL CHECK(publication_mode IN('TEST','TELEGRAM')),
 UNIQUE(subject,request_id),
 FOREIGN KEY(market,provider,ticker,product,contract) REFERENCES lab_level_catalog_v110(market,provider,ticker,product,contract)
) STRICT;
CREATE INDEX lab_proposal_subject_day_v3019 ON lab_proposals_v3019(subject,received_utc);
CREATE TABLE lab_proposal_outbox_v3019 (
 proposal_id INTEGER PRIMARY KEY REFERENCES lab_proposals_v3019(id),
 epoch INTEGER NOT NULL CHECK(epoch>=1),
 state TEXT NOT NULL CHECK(state IN('PENDING','SENDING','SENT','UNKNOWN','BLOCKED')),
 queued_utc TEXT NOT NULL,claimed_utc TEXT,finished_utc TEXT,message_id INTEGER,
 CHECK((state='PENDING' AND claimed_utc IS NULL AND finished_utc IS NULL AND message_id IS NULL)
 OR (state='SENDING' AND claimed_utc IS NOT NULL AND finished_utc IS NULL AND message_id IS NULL)
 OR (state='SENT' AND claimed_utc IS NOT NULL AND finished_utc IS NOT NULL AND message_id IS NOT NULL AND message_id>0)
 OR (state IN('UNKNOWN','BLOCKED') AND claimed_utc IS NOT NULL AND finished_utc IS NOT NULL AND message_id IS NULL))
) STRICT;
CREATE TRIGGER lab_proposal_guard_v3019 BEFORE INSERT ON lab_proposals_v3019 BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s
 WHERE i.subject=NEW.subject AND i.email_tag=NEW.email_tag AND i.revoked=0 AND s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0
 AND (NEW.publication_mode='TEST' OR i.slot IN('friend-b','friend-c'))) THEN RAISE(ABORT,'proposal_denied') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_level_catalog_v110 c WHERE
 (c.market,c.provider,c.ticker,c.product,c.contract,c.source_group)=(NEW.market,NEW.provider,NEW.ticker,NEW.product,NEW.contract,NEW.source_group) AND c.active=1) THEN RAISE(ABORT,'mapping_denied') END;
 SELECT CASE WHEN NEW.publication_mode='TELEGRAM' AND (instr(upper(NEW.note),'TEST')>0 OR instr(upper(NEW.note),'COLLAUDO')>0 OR instr(upper(NEW.note),'NON OPERATIVO')>0 OR instr(upper(NEW.note),'NON-OPERATIVO')>0) THEN RAISE(ABORT,'test_denied') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM json_each(NEW.prices_json) WHERE type<>'text' OR length(value)>17 OR value GLOB '*[^0-9.]*' OR value NOT GLOB '*[1-9]*' OR length(value)-length(replace(value,'.',''))>1)
 OR (SELECT COUNT(DISTINCT value) FROM json_each(NEW.prices_json))<>json_array_length(NEW.prices_json) THEN RAISE(ABORT,'prices_invalid') END;
 SELECT CASE WHEN json_array_length(NEW.prices_json)
 + (SELECT COUNT(*) FROM lab_level_attempts_v110 WHERE subject=NEW.subject AND duplicate_of IS NULL AND substr(received_utc,1,10)=substr(NEW.received_utc,1,10))
 + (SELECT COALESCE(SUM(json_array_length(prices_json)),0) FROM lab_proposals_v3019 WHERE subject=NEW.subject AND substr(received_utc,1,10)=substr(NEW.received_utc,1,10))>20 THEN RAISE(ABORT,'capacity') END;
 SELECT CASE WHEN 1
 + (SELECT COUNT(*) FROM lab_level_attempts_v110 WHERE subject=NEW.subject AND substr(received_utc,1,10)=substr(NEW.received_utc,1,10))
 + (SELECT COUNT(*) FROM lab_proposals_v3019 WHERE subject=NEW.subject AND substr(received_utc,1,10)=substr(NEW.received_utc,1,10))>60 THEN RAISE(ABORT,'capacity') END;
END;
CREATE TRIGGER lab_proposal_enqueue_v3019 AFTER INSERT ON lab_proposals_v3019 WHEN NEW.publication_mode='TELEGRAM' AND NEW.provider<>'ECB' BEGIN
 INSERT INTO lab_proposal_outbox_v3019(proposal_id,epoch,state,queued_utc)
 SELECT NEW.id,p.epoch,'PENDING',NEW.received_utc FROM lab_telegram_policy_v3012 p
 JOIN lab_telegram_sources_v3012 m ON (m.market,m.provider,m.ticker,m.product,m.contract)=(NEW.market,NEW.provider,NEW.ticker,NEW.product,NEW.contract)
 WHERE p.id=1 AND p.enabled=1;
END;
CREATE TRIGGER lab_proposal_no_update_v3019 BEFORE UPDATE ON lab_proposals_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_proposal_no_delete_v3019 BEFORE DELETE ON lab_proposals_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_proposal_outbox_guard_v3019 BEFORE UPDATE ON lab_proposal_outbox_v3019 BEGIN
 SELECT CASE WHEN NEW.proposal_id<>OLD.proposal_id OR NEW.epoch<>OLD.epoch OR NEW.queued_utc<>OLD.queued_utc OR NOT(
 (OLD.state='PENDING' AND NEW.state='SENDING') OR
 (OLD.state='SENDING' AND NEW.state IN('SENT','UNKNOWN','BLOCKED') AND NEW.claimed_utc=OLD.claimed_utc)) THEN RAISE(ABORT,'transition_denied') END;
END;
CREATE TRIGGER lab_proposal_outbox_no_delete_v3019 BEFORE DELETE ON lab_proposal_outbox_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;

-- SOURCE proposal-approval.sql git blob 6d2ac6e021911d395295068f8391e9afd7c4ced0
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

-- SOURCE proposal-release-realm.sql git blob 39f3aed18e11371e68624c1ecdd9f13697022e19
-- V30.19 candidate only. Apply after preflight + proposal-schema + proposal-approval,
-- in the SAME verified atomic transaction. Never apply to an existing populated LAB ledger.
CREATE TABLE lab_delivery_realm_v3019(id INTEGER PRIMARY KEY CHECK(id=1),realm TEXT NOT NULL CHECK(realm='STAGING_CANDIDATE')) STRICT;
CREATE TRIGGER lab_realm_install_guard_v3019 BEFORE INSERT ON lab_delivery_realm_v3019 BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM lab_delivery_realm_v3019)
 OR EXISTS(SELECT 1 FROM lab_proposals_v3019)
 OR EXISTS(SELECT 1 FROM lab_proposal_outbox_v3019)
 OR NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=0 AND recovery_enabled=0)
 OR NOT EXISTS(SELECT 1 FROM lab_telegram_policy_v3012 WHERE id=1 AND enabled=0)
 THEN RAISE(ABORT,'realm_install_denied') END;
END;
INSERT INTO lab_delivery_realm_v3019 VALUES(1,'STAGING_CANDIDATE');
CREATE TRIGGER lab_realm_no_update_v3019 BEFORE UPDATE ON lab_delivery_realm_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER lab_realm_no_delete_v3019 BEFORE DELETE ON lab_delivery_realm_v3019 BEGIN SELECT RAISE(ABORT,'immutable'); END;
