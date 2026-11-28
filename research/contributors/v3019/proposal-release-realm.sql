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
