-- REMURA Contributors v1.10 LAB. Run as one atomic migration after staging-slots-v110.sql.
-- Existing access rows and gates are carried forward. Catalog and operational data start empty.
CREATE TABLE lab_levels_migration_guard_v110 (ok INTEGER NOT NULL CHECK(ok=1)) STRICT;
INSERT INTO lab_levels_migration_guard_v110 VALUES (CASE WHEN
 (SELECT COUNT(*) FROM sqlite_schema WHERE type='table' AND name NOT GLOB 'sqlite_*'
   AND name NOT IN('_cf_KV','lab_levels_migration_guard_v110'))=3
 AND EXISTS(SELECT 1 FROM sqlite_schema WHERE type='table' AND name='lab_identities'
   AND instr(sql, '''friend-a'',''friend-b'',''friend-c''')>0)
 AND EXISTS(SELECT 1 FROM sqlite_schema WHERE type='table' AND name='lab_state'
   AND instr(replace(sql,' ',''), 'CHECK(write_enabled=0)')>0)
 AND (SELECT COUNT(*) FROM sqlite_schema WHERE type='trigger'
   AND name IN ('staging_owner_no_overlap_insert','staging_owner_no_overlap_update',
                'staging_contributor_no_overlap_insert','staging_contributor_no_overlap_update'))=4
 AND (SELECT COUNT(*) FROM sqlite_schema WHERE type='trigger')=4
 AND (SELECT COUNT(*) FROM sqlite_schema WHERE type='view' OR (type='index' AND sql IS NOT NULL))=0
 AND (SELECT COUNT(*) FROM lab_state)=1
 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=0 AND recovery_enabled=0)
 AND (SELECT COUNT(*) FROM lab_owner)=1 AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND revoked=0)
 AND (SELECT COUNT(*) FROM lab_identities)=1 AND EXISTS(SELECT 1 FROM lab_identities WHERE slot='friend-a' AND revoked=0)
 THEN 1 ELSE 0 END);

CREATE TABLE lab_state_v110 (
 id INTEGER PRIMARY KEY CHECK(id=1),
 write_enabled INTEGER NOT NULL DEFAULT 0 CHECK(write_enabled IN(0,1)),
 read_enabled INTEGER NOT NULL DEFAULT 0 CHECK(read_enabled IN(0,1)),
 recovery_enabled INTEGER NOT NULL DEFAULT 0 CHECK(recovery_enabled IN(0,1))
) STRICT;
INSERT INTO lab_state_v110 (id,write_enabled,read_enabled,recovery_enabled)
 SELECT id,write_enabled,read_enabled,recovery_enabled FROM lab_state;
DROP TABLE lab_state;
ALTER TABLE lab_state_v110 RENAME TO lab_state;

CREATE TRIGGER lab_contributor_immutable_v110 BEFORE UPDATE ON lab_identities
 WHEN OLD.subject<>NEW.subject OR OLD.email_tag<>NEW.email_tag OR OLD.slot<>NEW.slot OR NEW.revoked<OLD.revoked
 BEGIN SELECT RAISE(ABORT,'identity_immutable'); END;
CREATE TRIGGER lab_contributor_no_delete_v110 BEFORE DELETE ON lab_identities
 BEGIN SELECT RAISE(ABORT,'identity_immutable'); END;
CREATE TRIGGER lab_contributor_no_replace_v110 BEFORE INSERT ON lab_identities
 WHEN EXISTS(SELECT 1 FROM lab_identities WHERE slot=NEW.slot OR subject=NEW.subject OR email_tag=NEW.email_tag)
 BEGIN SELECT RAISE(ABORT,'identity_already_bound'); END;
CREATE TRIGGER lab_owner_immutable_v110 BEFORE UPDATE ON lab_owner
 WHEN OLD.id<>NEW.id OR OLD.subject<>NEW.subject OR OLD.email_tag<>NEW.email_tag OR NEW.revoked<OLD.revoked
 BEGIN SELECT RAISE(ABORT,'identity_immutable'); END;
CREATE TRIGGER lab_owner_no_delete_v110 BEFORE DELETE ON lab_owner
 BEGIN SELECT RAISE(ABORT,'identity_immutable'); END;
CREATE TRIGGER lab_owner_no_replace_v110 BEFORE INSERT ON lab_owner
 WHEN EXISTS(SELECT 1 FROM lab_owner WHERE id=NEW.id OR subject=NEW.subject OR email_tag=NEW.email_tag)
 BEGIN SELECT RAISE(ABORT,'identity_already_bound'); END;

-- Operator-approved mappings only. No fixture rows or data source activation.
CREATE TABLE lab_level_catalog_v110 (
 market TEXT NOT NULL CHECK(length(market) BETWEEN 1 AND 24 AND market NOT GLOB '*[^A-Z0-9_]*'),
 provider TEXT NOT NULL CHECK(length(provider) BETWEEN 1 AND 16 AND provider NOT GLOB '*[^A-Z0-9_]*'),
 ticker TEXT NOT NULL CHECK(length(ticker) BETWEEN 1 AND 24 AND ticker NOT GLOB '*[^A-Z0-9_.!-]*'),
 product TEXT NOT NULL CHECK(product IN('SPOT','CFD','FUTURE','INDEX')),
 contract TEXT NOT NULL,
 source_group TEXT NOT NULL CHECK(length(source_group) BETWEEN 1 AND 64),
 active INTEGER NOT NULL CHECK(active IN(0,1)),
 PRIMARY KEY(market,provider,ticker,product,contract),
 CHECK((product='FUTURE' AND length(contract) BETWEEN 1 AND 24 AND contract NOT GLOB '*[^A-Z0-9_.-]*'
        AND instr(ticker,'!')=0) OR (product<>'FUTURE' AND contract=''))
) STRICT;

-- Each normalized request gets a durable row in the same statement as its receipt.
-- A canonical row is the receipt. An equivalent later request points at that receipt.
CREATE TABLE lab_level_attempts_v110 (
 id INTEGER PRIMARY KEY CHECK(id>0),
 subject TEXT NOT NULL REFERENCES lab_identities(subject),
 email_tag TEXT NOT NULL CHECK(length(email_tag)=64 AND email_tag NOT GLOB '*[^0-9a-f]*'),
 request_id TEXT NOT NULL CHECK(length(request_id)=36 AND request_id NOT GLOB '*[^0-9a-f-]*'),
 fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64 AND fingerprint NOT GLOB '*[^0-9a-f]*'),
 market TEXT NOT NULL,
 provider TEXT NOT NULL,
 ticker TEXT NOT NULL,
 product TEXT NOT NULL,
 contract TEXT NOT NULL,
 period TEXT NOT NULL CHECK(period IN('DAY','WEEK','CURRENT_MONTH','PREVIOUS_MONTH')),
 kind TEXT NOT NULL CHECK(kind IN('DELTA_PEAK','EFFORT_RESULT','OTHER_VOLUME_LEVEL')),
 price TEXT NOT NULL CHECK(length(price) BETWEEN 1 AND 17 AND price NOT GLOB '*[^0-9.]*'
  AND price GLOB '*[1-9]*' AND length(price)-length(replace(price,'.',''))<=1),
 anchor_utc TEXT NOT NULL CHECK(length(anchor_utc)=20 AND anchor_utc GLOB '????-??-??T??:??:??Z'),
 observed_utc TEXT NOT NULL CHECK(length(observed_utc)=20 AND observed_utc GLOB '????-??-??T??:??:??Z'),
 received_utc TEXT NOT NULL CHECK(length(received_utc)=20 AND received_utc GLOB '????-??-??T??:??:??Z'),
 note TEXT NOT NULL CHECK(length(note)<=280),
 source_group TEXT NOT NULL,
 duplicate_of INTEGER REFERENCES lab_level_attempts_v110(id),
 CHECK(anchor_utc<=observed_utc AND observed_utc<=received_utc),
 UNIQUE(subject,request_id),
 FOREIGN KEY(market,provider,ticker,product,contract)
  REFERENCES lab_level_catalog_v110(market,provider,ticker,product,contract)
) STRICT;
CREATE UNIQUE INDEX lab_level_canonical_v110
 ON lab_level_attempts_v110(subject,market,provider,ticker,product,contract,period,kind,price,anchor_utc)
 WHERE duplicate_of IS NULL;
CREATE INDEX lab_level_personal_v110
 ON lab_level_attempts_v110(subject,id) WHERE duplicate_of IS NULL;
CREATE INDEX lab_level_daily_v110
 ON lab_level_attempts_v110(subject,received_utc) WHERE duplicate_of IS NULL;
CREATE INDEX lab_attempt_daily_v110 ON lab_level_attempts_v110(subject,received_utc);
CREATE TABLE lab_level_pending_v110 (
 entry_id INTEGER PRIMARY KEY REFERENCES lab_level_attempts_v110(id)
) STRICT;

CREATE TRIGGER lab_level_attempt_guard_v110 BEFORE INSERT ON lab_level_attempts_v110 BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM lab_level_attempts_v110 WHERE id=NEW.id)
 OR EXISTS(SELECT 1 FROM lab_level_attempts_v110 WHERE subject=NEW.subject AND request_id=NEW.request_id)
 THEN RAISE(ABORT,'attempt_immutable') END;
 SELECT CASE WHEN NOT EXISTS(
  SELECT 1 FROM lab_identities i CROSS JOIN lab_state s
  WHERE i.subject=NEW.subject AND i.email_tag=NEW.email_tag AND i.revoked=0
   AND s.id=1 AND s.read_enabled=1 AND s.write_enabled=1
 ) THEN RAISE(ABORT,'intake_denied') END;
 SELECT CASE WHEN NOT EXISTS(
  SELECT 1 FROM lab_level_catalog_v110 c
  WHERE c.market=NEW.market AND c.provider=NEW.provider AND c.ticker=NEW.ticker
   AND c.product=NEW.product AND c.contract=NEW.contract AND c.source_group=NEW.source_group AND c.active=1
 ) THEN RAISE(ABORT,'mapping_denied') END;
 SELECT CASE WHEN NEW.duplicate_of IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM lab_level_attempts_v110 e
  WHERE e.id=NEW.duplicate_of AND e.duplicate_of IS NULL AND e.subject=NEW.subject AND e.email_tag=NEW.email_tag
   AND (e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc)=
       (NEW.market,NEW.provider,NEW.ticker,NEW.product,NEW.contract,NEW.period,NEW.kind,NEW.price,NEW.anchor_utc)
 ) THEN RAISE(ABORT,'duplicate_ownership') END;
 SELECT CASE WHEN NEW.duplicate_of IS NULL AND EXISTS(
  SELECT 1 FROM lab_level_attempts_v110 e
  WHERE e.subject=NEW.subject AND e.duplicate_of IS NULL
   AND (e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc)=
       (NEW.market,NEW.provider,NEW.ticker,NEW.product,NEW.contract,NEW.period,NEW.kind,NEW.price,NEW.anchor_utc)
 ) THEN RAISE(ABORT,'canonical_attempt_immutable') END;
 SELECT CASE WHEN NEW.duplicate_of IS NULL AND EXISTS(
  SELECT 1 FROM lab_level_attempts_v110 e WHERE e.subject=NEW.subject AND e.duplicate_of IS NULL
   AND e.received_utc BETWEEN substr(NEW.received_utc,1,10)||'T00:00:00Z'
                          AND substr(NEW.received_utc,1,10)||'T23:59:59Z'
  LIMIT 1 OFFSET 19
 ) THEN RAISE(ABORT,'intake_capacity') END;
 SELECT CASE WHEN EXISTS(
  SELECT 1 FROM lab_level_attempts_v110 e WHERE e.subject=NEW.subject
   AND e.received_utc BETWEEN substr(NEW.received_utc,1,10)||'T00:00:00Z'
                          AND substr(NEW.received_utc,1,10)||'T23:59:59Z'
  LIMIT 1 OFFSET 59
 ) THEN RAISE(ABORT,'attempt_capacity') END;
END;
CREATE TRIGGER lab_level_queue_v110 AFTER INSERT ON lab_level_attempts_v110 WHEN NEW.duplicate_of IS NULL BEGIN
 INSERT INTO lab_level_pending_v110(entry_id) VALUES(NEW.id);
END;
CREATE TRIGGER lab_level_no_update_v110 BEFORE UPDATE ON lab_level_attempts_v110
 BEGIN SELECT RAISE(ABORT,'attempt_immutable'); END;
CREATE TRIGGER lab_level_no_delete_v110 BEFORE DELETE ON lab_level_attempts_v110
 BEGIN SELECT RAISE(ABORT,'attempt_immutable'); END;

-- Append-only decisions and slot activity. Private identity tags have no read projection.
CREATE TABLE lab_activity_v110 (
 id INTEGER PRIMARY KEY CHECK(id>0),
 entry_id INTEGER REFERENCES lab_level_attempts_v110(id),
 slot TEXT CHECK(slot IN('friend-a','friend-b','friend-c')),
 action TEXT NOT NULL,
 at_utc TEXT NOT NULL CHECK(length(at_utc)=20 AND at_utc GLOB '????-??-??T??:??:??Z'),
 reason TEXT NOT NULL DEFAULT '' CHECK(length(reason)<=280),
 invite_email_tag TEXT CHECK(length(invite_email_tag)=64 AND invite_email_tag NOT GLOB '*[^0-9a-f]*'),
 enrollment_subject TEXT CHECK(length(enrollment_subject)=64 AND enrollment_subject NOT GLOB '*[^0-9a-f]*'),
 CHECK(
  (action IN('APPROVED','REJECTED') AND entry_id IS NOT NULL AND slot IS NULL
   AND length(trim(reason))>0 AND invite_email_tag IS NULL AND enrollment_subject IS NULL)
  OR
  (entry_id IS NULL AND slot IS NOT NULL AND reason='' AND (
   (action='INVITED' AND slot IN('friend-b','friend-c') AND invite_email_tag IS NOT NULL AND enrollment_subject IS NULL)
   OR (action='ENROLLED' AND slot IN('friend-b','friend-c') AND invite_email_tag IS NOT NULL AND enrollment_subject IS NOT NULL)
   OR (action='WITHDRAWN' AND slot IN('friend-b','friend-c') AND invite_email_tag IS NULL AND enrollment_subject IS NULL)
   OR (action='REVOKED' AND invite_email_tag IS NULL AND enrollment_subject IS NULL)
  ))
 )
) STRICT;
CREATE UNIQUE INDEX lab_level_single_decision_v110 ON lab_activity_v110(entry_id);
CREATE INDEX lab_slot_revision_v110 ON lab_activity_v110(slot,id DESC);

CREATE VIEW lab_slot_status_v110 AS
 WITH slots(slot) AS (VALUES('friend-a'),('friend-b'),('friend-c'))
 SELECT s.slot,
  CASE WHEN i.revoked=1 THEN 'REVOKED'
       WHEN i.slot IS NOT NULL THEN 'ACTIVE'
       WHEN a.action='INVITED' THEN 'INVITED'
       ELSE 'VACANT' END AS status,
  COALESCE(a.id,0) AS revision,
  CASE WHEN a.action='INVITED' AND i.slot IS NULL THEN a.invite_email_tag ELSE NULL END AS invite_email_tag
 FROM slots s LEFT JOIN lab_identities i ON i.slot=s.slot
 LEFT JOIN lab_activity_v110 a ON a.id=(SELECT x.id FROM lab_activity_v110 x WHERE x.slot=s.slot ORDER BY x.id DESC LIMIT 1);

CREATE TRIGGER lab_activity_guard_v110 BEFORE INSERT ON lab_activity_v110 BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM lab_activity_v110 WHERE id=NEW.id)
 OR EXISTS(SELECT 1 FROM lab_activity_v110 WHERE entry_id=NEW.entry_id)
 THEN RAISE(ABORT,'activity_immutable') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=1)
 THEN RAISE(ABORT,'activity_disabled') END;
 SELECT CASE WHEN NEW.entry_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM lab_level_attempts_v110 e
  WHERE e.id=NEW.entry_id AND e.duplicate_of IS NULL AND e.received_utc<=NEW.at_utc
 ) THEN RAISE(ABORT,'decision_target') END;
 SELECT CASE WHEN NEW.action='APPROVED' AND NOT EXISTS(
  SELECT 1 FROM lab_level_attempts_v110 e
  JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag AND i.revoked=0
  JOIN lab_level_catalog_v110 c USING(market,provider,ticker,product,contract)
  WHERE e.id=NEW.entry_id AND c.active=1 AND c.source_group=e.source_group
 ) THEN RAISE(ABORT,'approval_source_denied') END;
 SELECT CASE WHEN NEW.action='INVITED' AND (
  NOT EXISTS(SELECT 1 FROM lab_slot_status_v110 WHERE slot=NEW.slot AND status='VACANT')
  OR EXISTS(SELECT 1 FROM lab_slot_status_v110 WHERE invite_email_tag=NEW.invite_email_tag)
  OR EXISTS(SELECT 1 FROM lab_owner WHERE email_tag=NEW.invite_email_tag)
  OR EXISTS(SELECT 1 FROM lab_identities WHERE email_tag=NEW.invite_email_tag)
 ) THEN RAISE(ABORT,'slot_invite_denied') END;
 SELECT CASE WHEN NEW.action='WITHDRAWN' AND NOT EXISTS(
  SELECT 1 FROM lab_slot_status_v110 WHERE slot=NEW.slot AND status='INVITED'
 ) THEN RAISE(ABORT,'slot_withdraw_denied') END;
 SELECT CASE WHEN NEW.action='ENROLLED' AND NOT EXISTS(
  SELECT 1 FROM lab_slot_status_v110 WHERE slot=NEW.slot AND status='INVITED' AND invite_email_tag=NEW.invite_email_tag
 ) THEN RAISE(ABORT,'slot_enroll_denied') END;
 SELECT CASE WHEN NEW.action='REVOKED' AND NOT EXISTS(
  SELECT 1 FROM lab_identities WHERE slot=NEW.slot AND revoked=0
 ) THEN RAISE(ABORT,'slot_revoke_denied') END;
END;
CREATE TRIGGER lab_activity_apply_enrollment_v110 AFTER INSERT ON lab_activity_v110 WHEN NEW.action='ENROLLED' BEGIN
 INSERT INTO lab_identities(slot,subject,email_tag,revoked) VALUES(NEW.slot,NEW.enrollment_subject,NEW.invite_email_tag,0);
END;
CREATE TRIGGER lab_activity_apply_revocation_v110 AFTER INSERT ON lab_activity_v110 WHEN NEW.action='REVOKED' BEGIN
 UPDATE lab_identities SET revoked=1 WHERE slot=NEW.slot AND revoked=0;
END;
CREATE TRIGGER lab_activity_dequeue_v110 AFTER INSERT ON lab_activity_v110 WHEN NEW.entry_id IS NOT NULL BEGIN
 DELETE FROM lab_level_pending_v110 WHERE entry_id=NEW.entry_id;
END;
CREATE TRIGGER lab_activity_no_update_v110 BEFORE UPDATE ON lab_activity_v110
 BEGIN SELECT RAISE(ABORT,'activity_immutable'); END;
CREATE TRIGGER lab_activity_no_delete_v110 BEFORE DELETE ON lab_activity_v110
 BEGIN SELECT RAISE(ABORT,'activity_immutable'); END;

DROP TABLE lab_levels_migration_guard_v110;
