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
