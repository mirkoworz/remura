# REMURA Contributors v0.80 LAB — new tests, offline synthetic evidence only.
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

import readiness_dossier_v080_lab as rd

NOW = datetime(2026, 11, 21, 17, 30, tzinfo=timezone.utc)
DB1 = "12345678-1234-1234-1234-123456789abc"
DB2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
IDS = [{"uuid": DB1}, {"uuid": DB2}]


def groups(day, *rows):
    return {"data": {"viewer": {"accounts": [{
        "d1AnalyticsAdaptiveGroups": [
            {"dimensions": {"date": day, "databaseId": uid},
             "sum": {"rowsRead": reads, "rowsWritten": writes}}
            for uid, reads, writes in rows
        ]
    }]}}}


def evidence():
    return {
        "d1": (
            "REMURA_CF_ACCOUNT_QUOTA=OK\n"
            "UTC_DAY=2026-11-21; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\n"
            "D1_ACCOUNT_ROWS_READ_ESTIMATE=196\n"
            "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=784\n"
            "D1_FREE_READ_LIMIT=5000000\n"
            "D1_FREE_WRITE_LIMIT=100000\n"
        ),
        "workers": (
            "REMURA_CF_WORKERS_USAGE=OK\n"
            "WORKERS_UTC_DAY=2026-11-21; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\n"
            "WORKERS_ACCOUNT_REQUESTS_ESTIMATE=199\n"
            "WORKERS_ACCOUNT_ERRORS_ESTIMATE=0\n"
            "WORKERS_FREE_DAILY_REQUEST_LIMIT=100000\n"
        ),
        "test_storage": (
            "REMURA_D1_TEST_STORAGE=OK\n"
            "REMURA_D1_TEST_STORAGE_BYTES=6266880\n"
            "REMURA_D1_TEST_STORAGE_LIMIT_BYTES=500000000\n"
        ),
        "account_storage": (
            "REMURA_D1_ACCOUNT_STORAGE=OK\n"
            "D1_ACCOUNT_DATABASE_COUNT=4\n"
            "D1_ACCOUNT_STORAGE_BYTES=6557696\n"
            "D1_ACCOUNT_LARGEST_DB_BYTES=6266880\n"
            "D1_ACCOUNT_FREE_STORAGE_LIMIT_BYTES=5000000000\n"
            "D1_ACCOUNT_FREE_SINGLE_DB_LIMIT_BYTES=500000000\n"
            "D1_ACCOUNT_FREE_DB_COUNT_LIMIT=10\n"
        )
    }


def access():
    return {"plan": "FREE", "seats_used": 2, "seats_total": 50,
            "observed_utc": "2026-11-21T17:20:00Z",
            "source": "MANUAL_ZERO_TRUST_DASHBOARD"}


def monitor():
    return {"run_id": 44919682812, "head_branch": "main",
            "conclusion": "success", "started_utc": "2026-11-21T15:32:05Z",
            "source": "GITHUB_ACTIONS_PUBLIC_RUN"}


def dossier(**changes):
    args = dict(logs=evidence(), now_utc=NOW, monitor=monitor(), access=access(),
                graphql_today=groups("2026-11-21", (DB1, 196, 784)),
                graphql_yesterday=groups("2026-11-20", (DB1, 250, 900)),
                inventory=IDS)
    args.update(changes)
    return rd.dossier(**args)


class ReadinessCases(unittest.TestCase):
    def test_01_perfect_fixture_is_still_no_go(self):
        self.assertEqual(dossier().decision, "NO_GO")

    def test_02_no_real_quota_attestation(self):
        self.assertFalse(dossier().public_dict()["real_cloudflare_quotas_attested"])

    def test_03_automatic_deploy_never_allowed(self):
        self.assertFalse(dossier().public_dict()["automatic_deploy_allowed"])

    def test_04_explicit_authorization_always_required(self):
        self.assertTrue(dossier().public_dict()["requires_explicit_staging_authorization"])

    def test_05_source_lock_matches_v078(self):
        self.assertEqual(dossier().source_lock, "LAB_SOURCE_LOCK_MATCH")

    def test_06_d1_today_synthetic_groups_not_billing(self):
        self.assertEqual(dossier().graphql_triage, "TODAY_GROUPS_PRESENT_OFFLINE_ONLY")

    def test_07_graphql_offline_cannot_attest_provider(self):
        self.assertIn("D1_GRAPHQL_OFFLINE_INPUT_NOT_PROVIDER_PROOF", dossier().reasons)

    def test_08_manual_access_does_not_attest_provider(self):
        d=dossier()
        self.assertEqual(d.access,"MANUAL_ONLY")
        self.assertIn("ACCESS_SEATS_MANUAL_NOT_PROVIDER_ATTESTED",d.reasons)

    def test_09_no_access_is_unknown(self):
        d=dossier(access=None)
        self.assertEqual(d.access,"UNKNOWN")
        self.assertIn("ACCESS_SEATS_UNMEASURED",d.reasons)

    def test_10_wrong_access_plan_denied(self):
        a=access();a["plan"]="PAID"
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_11_manual_access_source_must_be_exact(self):
        a=access();a["source"]="WEB_SEARCH"
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_12_access_no_free_seats(self):
        a=access();a["seats_used"]=50
        self.assertEqual(dossier(access=a).access,"NO_CAPACITY")

    def test_13_access_over_free_seat_reference(self):
        a=access();a["seats_total"]=51
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_14_access_used_exceeds_total(self):
        a=access();a["seats_used"]=51
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_15_access_old_snapshot_is_stale(self):
        a=access();a["observed_utc"]="2026-11-21T12:00:00Z"
        self.assertEqual(dossier(access=a).access,"STALE")

    def test_16_access_previous_day_is_stale(self):
        a=access();a["observed_utc"]="2026-11-20T23:50:00Z"
        self.assertEqual(dossier(access=a).access,"STALE")

    def test_17_access_future_over_skew_is_stale(self):
        a=access();a["observed_utc"]="2026-11-21T17:33:00Z"
        self.assertEqual(dossier(access=a).access,"STALE")

    def test_18_access_bad_timestamp_is_invalid(self):
        a=access();a["observed_utc"]="21-11-2026"
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_19_access_negative_seats_invalid(self):
        a=access();a["seats_used"]=-1
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_20_access_unexpected_field_invalid(self):
        a=access();a["email"]="someone@example.com"
        self.assertEqual(dossier(access=a).access,"INVALID")

    def test_21_successful_monitor_metadata_not_provider_proof(self):
        self.assertEqual(dossier().monitor,"PUBLIC_METADATA_ONLY")

    def test_22_failed_real_monitor_remains_incomplete(self):
        m=monitor();m["conclusion"]="failure"
        d=dossier(monitor=m)
        self.assertEqual(d.monitor,"INCOMPLETE")
        self.assertIn("MONITOR_RUN_FAILED_OR_INCOMPLETE",d.reasons)

    def test_23_old_monitor_is_stale(self):
        m=monitor();m["started_utc"]="2026-11-21T10:00:00Z"
        self.assertEqual(dossier(monitor=m).monitor,"STALE")

    def test_24_monitor_previous_day_is_stale(self):
        m=monitor();m["started_utc"]="2026-11-20T23:59:00Z"
        self.assertEqual(dossier(monitor=m).monitor,"STALE")

    def test_25_monitor_wrong_branch_invalid(self):
        m=monitor();m["head_branch"]="develop"
        self.assertEqual(dossier(monitor=m).monitor,"INVALID")

    def test_26_monitor_zero_id_invalid(self):
        m=monitor();m["run_id"]=0
        self.assertEqual(dossier(monitor=m).monitor,"INVALID")

    def test_27_monitor_boolean_id_invalid(self):
        m=monitor();m["run_id"]=True
        self.assertEqual(dossier(monitor=m).monitor,"INVALID")

    def test_28_monitor_unknown_conclusion_invalid(self):
        m=monitor();m["conclusion"]="skipped"
        self.assertEqual(dossier(monitor=m).monitor,"INVALID")

    def test_29_monitor_wrong_source_invalid(self):
        m=monitor();m["source"]="CLOUDFLARE_BILLING_EXACT"
        self.assertEqual(dossier(monitor=m).monitor,"INVALID")

    def test_30_monitor_missing_is_invalid(self):
        self.assertEqual(dossier(monitor=None).monitor,"INVALID")

    def test_31_empty_today_prior_present_is_unknown(self):
        d=dossier(graphql_today=groups("2026-11-21"))
        self.assertEqual(d.graphql_triage,"TODAY_EMPTY_PRIOR_PRESENT")
        self.assertIn("D1_TODAY_EMPTY_NOT_ZERO",d.reasons)

    def test_32_empty_today_and_yesterday_is_unknown(self):
        d=dossier(graphql_today=groups("2026-11-21"),
                  graphql_yesterday=groups("2026-11-20"))
        self.assertEqual(d.graphql_triage,"BOTH_DAYS_EMPTY")

    def test_33_graphql_no_payload_is_not_available(self):
        self.assertEqual(dossier(graphql_today=None).graphql_triage,"NOT_AVAILABLE")

    def test_34_graphql_errors_do_not_leak(self):
        d=dossier(graphql_today={"errors":[{"message":"SECRET_TOKEN"}]})
        self.assertEqual(d.graphql_triage,"INVALID")
        self.assertNotIn("SECRET_TOKEN",json.dumps(d.public_dict()))

    def test_35_graphql_wrong_day_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-20",(DB1,1,2))).graphql_triage,"INVALID")

    def test_36_graphql_unknown_database_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-21",("ffffffff-ffff-ffff-ffff-ffffffffffff",1,2))).graphql_triage,"INVALID")

    def test_37_graphql_duplicate_database_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-21",(DB1,1,2),(DB1,3,4))).graphql_triage,"INVALID")

    def test_38_graphql_two_accounts_invalid(self):
        p=groups("2026-11-21",(DB1,1,2))
        p["data"]["viewer"]["accounts"].append(p["data"]["viewer"]["accounts"][0])
        self.assertEqual(dossier(graphql_today=p).graphql_triage,"INVALID")

    def test_39_graphql_missing_viewer_invalid(self):
        self.assertEqual(dossier(graphql_today={"data":{}}).graphql_triage,"INVALID")

    def test_40_graphql_negative_rows_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-21",(DB1,-1,2))).graphql_triage,"INVALID")

    def test_41_graphql_fractional_rows_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-21",(DB1,1.5,2))).graphql_triage,"INVALID")

    def test_42_graphql_boolean_rows_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-21",(DB1,True,2))).graphql_triage,"INVALID")

    def test_43_graphql_infinite_rows_invalid(self):
        self.assertEqual(dossier(graphql_today=groups("2026-11-21",(DB1,float("inf"),2))).graphql_triage,"INVALID")

    def test_44_graphql_integer_float_is_allowed_as_estimate(self):
        r=rd.triage(groups("2026-11-21",(DB1,1.0,2.0)),
                    groups("2026-11-20"),day="2026-11-21",inventory=IDS)
        self.assertFalse(r["usage_attested"])

    def test_45_graphql_prior_data_not_used_as_today(self):
        r=rd.triage(groups("2026-11-21"),groups("2026-11-20",(DB1,999,999)),
                    day="2026-11-21",inventory=IDS)
        self.assertEqual(r["today"],"UNKNOWN_NOT_ZERO")
        self.assertNotIn("999",json.dumps(r))

    def test_46_invalid_inventory_empty(self):
        self.assertEqual(dossier(inventory=[]).graphql_triage,"INVALID")

    def test_47_inventory_duplicate(self):
        self.assertEqual(dossier(inventory=[IDS[0],IDS[0]]).graphql_triage,"INVALID")

    def test_48_inventory_more_than_10_invalid(self):
        values=[{"uuid":f"{i:08x}-1234-1234-1234-123456789abc"} for i in range(11)]
        self.assertEqual(dossier(inventory=values).graphql_triage,"INVALID")

    def test_49_inventory_with_email_rejected(self):
        self.assertEqual(dossier(inventory=[{"uuid":DB1,"email":"private"}]).graphql_triage,"INVALID")

    def test_50_source_lock_skipped_is_no_go(self):
        d=dossier(verify_sources=False)
        self.assertEqual(d.source_lock,"NOT_CHECKED")
        self.assertIn("SOURCE_LOCK_NOT_CHECKED",d.reasons)

    def test_51_source_lock_failure_is_no_go(self):
        with patch.object(rd,"verify_contract",side_effect=rd.SourceLockError("tampered")):
            d=dossier()
        self.assertEqual(d.source_lock,"DRIFT_OR_MISSING")
        self.assertIn("SOURCE_LOCK_FAILED",d.reasons)

    def test_52_real_21_nov_d1_unknown_still_no_go(self):
        e=evidence()
        e["d1"]="REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA\nREAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED\n"
        m=monitor();m["conclusion"]="failure"
        d=dossier(logs=e,monitor=m,graphql_today=groups("2026-11-21"))
        self.assertEqual(d.decision,"NO_GO")
        self.assertEqual(d.d1_daily,"UNKNOWN")
        self.assertEqual(d.monitor,"INCOMPLETE")
        self.assertIn("D1_DAILY_UNKNOWN_NOT_ZERO",d.reasons)

    def test_53_no_private_identifiers_in_public_dossier(self):
        d=dossier().public_dict()
        out=json.dumps(d)
        self.assertNotIn(DB1,out)
        self.assertNotIn("44919682812",out)
        self.assertNotIn("@",out)
        self.assertNotIn("seats_used",out)

    def test_54_invalid_budget_does_not_crash(self):
        self.assertEqual(dossier(logs={"bad":"data"}).d1_daily,"UNKNOWN")

    def test_55_non_utc_now_is_denied(self):
        with self.assertRaises(rd.DossierError):
            dossier(now_utc=datetime(2026,11,21,17,30,tzinfo=timezone(timedelta(hours=1))))

    def test_56_verify_sources_requires_bool(self):
        with self.assertRaises(rd.DossierError):
            dossier(verify_sources="yes")

    def test_57_cli_is_offline_help_only(self):
        with redirect_stdout(StringIO()) as out:
            rc=rd.main(["--offline-help"])
        self.assertEqual(rc,0)
        self.assertIn("OFFLINE_ONLY",out.getvalue())

    def test_58_cli_rejects_live_cloudflare_mode(self):
        with redirect_stdout(StringIO()) as out:
            rc=rd.main(["--cloudflare-live"])
        self.assertEqual(rc,3)
        self.assertIn("NO_GO",out.getvalue())

    def test_59_current_day_source_unknown_cannot_be_synthesized_from_graphql_fixture(self):
        e=evidence();e["d1"]="REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA\n"
        d=dossier(logs=e)
        self.assertEqual(d.d1_daily,"UNKNOWN")
        self.assertEqual(d.graphql_triage,"TODAY_GROUPS_PRESENT_OFFLINE_ONLY")
        self.assertEqual(d.decision,"NO_GO")

    def test_60_synthetic_dossier_is_never_a_real_cloudflare_audit(self):
        d=dossier().public_dict()
        self.assertEqual(d["input_trust"],"OFFLINE_SUPPLIED_UNVERIFIED")
        self.assertEqual(d["decision"],"NO_GO")
        self.assertFalse(d["real_cloudflare_quotas_attested"])


if __name__ == "__main__":
    unittest.main()
