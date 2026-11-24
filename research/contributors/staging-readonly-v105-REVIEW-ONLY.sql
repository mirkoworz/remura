-- REMURA Contributors v1.05 LAB — 24/11/2026 Europe/Rome.
-- REVIEW ONLY. Dedicated, confirmed empty remura-contributors-staging only.
-- Not a migration for existing databases. No identity enrollment or activation.
-- All gates OFF; separate approval for execution and later role provisioning.
CREATE TABLE lab_state (
  id INTEGER PRIMARY KEY CHECK (id=1),
  write_enabled INTEGER NOT NULL DEFAULT 0 CHECK (write_enabled=0),
  read_enabled INTEGER NOT NULL DEFAULT 0 CHECK (read_enabled IN (0,1)),
  recovery_enabled INTEGER NOT NULL DEFAULT 0 CHECK (recovery_enabled IN (0,1))
) STRICT;
CREATE TABLE lab_owner (
  id INTEGER PRIMARY KEY CHECK (id=1),
  subject TEXT NOT NULL UNIQUE CHECK (length(subject)=64 AND subject NOT GLOB '*[^0-9a-f]*'),
  email_tag TEXT NOT NULL UNIQUE CHECK (length(email_tag)=64 AND email_tag NOT GLOB '*[^0-9a-f]*'),
  revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0,1))
) STRICT;
CREATE TABLE lab_identities (
  slot TEXT PRIMARY KEY CHECK (slot IN ('friend-a','friend-b')),
  subject TEXT NOT NULL UNIQUE CHECK (length(subject)=64 AND subject NOT GLOB '*[^0-9a-f]*'),
  email_tag TEXT NOT NULL UNIQUE CHECK (length(email_tag)=64 AND email_tag NOT GLOB '*[^0-9a-f]*'),
  revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0,1))
) STRICT;
-- Disallow role overlap even when the other identity is revoked.
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
INSERT INTO lab_state(id,write_enabled,read_enabled,recovery_enabled) VALUES (1,0,0,0);
-- Intentionally no real or fixture identity, entry, review or catalog rows/tables.
-- A subsequent reviewed schema change is required before any write-enabled pilot.
