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
