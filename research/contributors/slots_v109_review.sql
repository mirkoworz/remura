-- REMURA v1.09 LAB: three slots, no write activation. REVIEW ONLY.
-- Execute as one atomic transaction in SQLite tests; real D1 batch requires approval.
CREATE TABLE lab_slot_migration_guard_v109 (ok INTEGER NOT NULL CHECK(ok=1)) STRICT;
INSERT INTO lab_slot_migration_guard_v109 VALUES (CASE WHEN
 (SELECT COUNT(*) FROM sqlite_schema WHERE type='table' AND name NOT GLOB 'sqlite_*' AND name<>'lab_slot_migration_guard_v109')=3
 AND EXISTS(SELECT 1 FROM sqlite_schema WHERE type='table' AND name='lab_identities' AND instr(sql, '''friend-a'',''friend-b''')>0 AND instr(sql, '''friend-c''')=0)
 AND (SELECT COUNT(*) FROM sqlite_schema WHERE type='trigger')=4
 AND (SELECT COUNT(*) FROM sqlite_schema WHERE type='view' OR (type='index' AND sql IS NOT NULL))=0
 AND (SELECT COUNT(*) FROM lab_state)=1
 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=0 AND recovery_enabled=0)
 AND (SELECT COUNT(*) FROM lab_owner)=1 AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND revoked=0)
 AND (SELECT COUNT(*) FROM lab_identities)=1 AND EXISTS(SELECT 1 FROM lab_identities WHERE slot='friend-a' AND revoked=0)
 THEN 1 ELSE 0 END);
CREATE TABLE lab_identities_v109 (
 slot TEXT PRIMARY KEY CHECK(slot IN ('friend-a','friend-b','friend-c')),
 subject TEXT NOT NULL UNIQUE CHECK(length(subject)=64 AND subject NOT GLOB '*[^0-9a-f]*'),
 email_tag TEXT NOT NULL UNIQUE CHECK(length(email_tag)=64 AND email_tag NOT GLOB '*[^0-9a-f]*'),
 revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1))
) STRICT;
INSERT INTO lab_identities_v109 SELECT slot,subject,email_tag,revoked FROM lab_identities;
INSERT INTO lab_slot_migration_guard_v109 VALUES (CASE WHEN
 NOT EXISTS(SELECT * FROM lab_identities EXCEPT SELECT * FROM lab_identities_v109)
 AND NOT EXISTS(SELECT * FROM lab_identities_v109 EXCEPT SELECT * FROM lab_identities)
 THEN 1 ELSE 0 END);
DROP TRIGGER staging_owner_no_overlap_insert;
DROP TRIGGER staging_owner_no_overlap_update;
DROP TRIGGER staging_contributor_no_overlap_insert;
DROP TRIGGER staging_contributor_no_overlap_update;
DROP TABLE lab_identities;
ALTER TABLE lab_identities_v109 RENAME TO lab_identities;
CREATE TRIGGER staging_owner_no_overlap_insert BEFORE INSERT ON lab_owner
WHEN EXISTS (SELECT 1 FROM lab_identities WHERE subject=NEW.subject OR email_tag=NEW.email_tag)
BEGIN SELECT RAISE(ABORT,'role_overlap'); END;
CREATE TRIGGER staging_owner_no_overlap_update BEFORE UPDATE ON lab_owner
WHEN EXISTS (SELECT 1 FROM lab_identities WHERE subject=NEW.subject OR email_tag=NEW.email_tag)
BEGIN SELECT RAISE(ABORT,'role_overlap'); END;
CREATE TRIGGER staging_contributor_no_overlap_insert BEFORE INSERT ON lab_identities
WHEN EXISTS (SELECT 1 FROM lab_owner WHERE subject=NEW.subject OR email_tag=NEW.email_tag)
BEGIN SELECT RAISE(ABORT,'role_overlap'); END;
CREATE TRIGGER staging_contributor_no_overlap_update BEFORE UPDATE ON lab_identities
WHEN EXISTS (SELECT 1 FROM lab_owner WHERE subject=NEW.subject OR email_tag=NEW.email_tag)
BEGIN SELECT RAISE(ABORT,'role_overlap'); END;
DROP TABLE lab_slot_migration_guard_v109;
