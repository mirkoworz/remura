-- REMURA Experience v0.14 LAB — 20/11/2026
-- SQLite-only fixture. Never apply to a live database.
PRAGMA foreign_keys=ON;
CREATE TABLE fixture_revision(
 revision INTEGER PRIMARY KEY CHECK(revision BETWEEN 1 AND 32),
 generation TEXT NOT NULL CHECK(generation='fixture-v014'),
 as_of TEXT NOT NULL CHECK(length(as_of)=20),
 digest TEXT NOT NULL CHECK(length(digest)=64 AND digest NOT GLOB '*[^0-9a-f]*'),
 payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB)) BETWEEN 1 AND 8192),
 UNIQUE(revision,generation,digest)
) STRICT;
CREATE TABLE fixture_head(
 id INTEGER PRIMARY KEY CHECK(id=1),
 revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 32),
 generation TEXT NOT NULL CHECK(generation='fixture-v014'),
 digest TEXT NOT NULL,
 FOREIGN KEY(revision,generation,digest) REFERENCES fixture_revision(revision,generation,digest)
) STRICT;
CREATE TRIGGER fixture_revision_sequence BEFORE INSERT ON fixture_revision
WHEN NEW.revision != COALESCE((SELECT revision FROM fixture_head WHERE id=1),0)+1
BEGIN SELECT RAISE(ABORT,'sequence'); END;
CREATE TRIGGER fixture_revision_no_update BEFORE UPDATE ON fixture_revision
BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER fixture_revision_no_delete BEFORE DELETE ON fixture_revision
BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER fixture_head_sequence BEFORE UPDATE ON fixture_head
WHEN NEW.revision != OLD.revision+1 OR NEW.generation != OLD.generation
BEGIN SELECT RAISE(ABORT,'sequence'); END;
CREATE TRIGGER fixture_head_first BEFORE INSERT ON fixture_head
WHEN NEW.revision != 1
BEGIN SELECT RAISE(ABORT,'first revision'); END;
CREATE TRIGGER fixture_head_no_delete BEFORE DELETE ON fixture_head
BEGIN SELECT RAISE(ABORT,'immutable'); END;
