# REMURA Contributors v0.80 LAB — NEW Access API synthetic pagination tests only.
from __future__ import annotations
import json
import unittest
from pathlib import Path
from access_seat_inventory_v080_lab import inspect_access_pages,inventory_summary,InventoryError,main


def uid(i):
    return f"{i:08x}-1111-4111-8111-111111111111"


def page(records, *, number=1, per_page=100, total=None, total_pages=1, **changes):
    if total is None:
        total=len(records)
    result={"success":True,"errors":[],"result":[dict(x) for x in records],
            "result_info":{"page":number,"per_page":per_page,"count":len(records),
                           "total_count":total,"total_pages":total_pages}}
    result.update(changes)
    return result


def user(i, flag=True):
    return {"id":uid(i),"access_seat":flag,
            "email":f"synthetic{i}@example.invalid","name":f"TEST USER {i}",
            "gateway_seat":False,"seat_uid":f"synthetic-seat-{i}"}


def fake(n=1, *, active=None):
    return [page([user(i,True if active is None else i<active) for i in range(n)])]


class AccessSeatInventoryV080Tests(unittest.TestCase):
    def assertDenied(self,data):
        with self.assertRaises(InventoryError):
            inspect_access_pages(data)

    def test_01_one_user_seen_but_billing_not_attested(self):
        s=inspect_access_pages(fake())
        self.assertEqual(s.status,"INVENTORY_FLAGS_PRESENT_BILLING_UNKNOWN")
        self.assertEqual(s.authenticated_user_flags,1)
        self.assertIsNone(s.seats_available)
        self.assertFalse(s.exact_billing_attested)

    def test_02_two_users_counted_without_email(self):
        s=inventory_summary(fake(2))
        self.assertEqual(s["users_counted"],2)
        self.assertEqual(s["access_authenticated_flags"],2)
        self.assertNotIn("email",str(s).lower())

    def test_03_false_access_flag_does_not_count_as_authenticated(self):
        self.assertEqual(inspect_access_pages(fake(3,active=1)).authenticated_user_flags,1)

    def test_04_reference_50_is_not_50_available(self):
        s=inventory_summary(fake(1))
        self.assertEqual(s["free_reference_seats"],50)
        self.assertIsNone(s["seats_available"])

    def test_05_34_access_flags_not_high(self):
        self.assertEqual(inspect_access_pages(fake(34)).status,"INVENTORY_FLAGS_PRESENT_BILLING_UNKNOWN")

    def test_06_35_access_flags_caution(self):
        self.assertEqual(inspect_access_pages(fake(35)).status,"AUTHENTICATED_FLAGS_HIGH_NEEDS_PLAN_REVIEW")

    def test_07_50_access_flags_caution(self):
        self.assertEqual(inspect_access_pages(fake(50)).status,"AUTHENTICATED_FLAGS_HIGH_NEEDS_PLAN_REVIEW")

    def test_08_empty_known_list_not_attested(self):
        s=inspect_access_pages([page([],total=0,total_pages=0)])
        self.assertEqual(s.status,"EMPTY_NOT_SEAT_ATTESTATION")
        self.assertIsNone(s.seats_available)

    def test_09_empty_single_pagination_page_1_considered_unknown(self):
        s=inspect_access_pages([page([],total=0,total_pages=1)])
        self.assertEqual(s.user_count,0)
        self.assertNotEqual(s.status,"INVENTORY_FLAGS_PRESENT_BILLING_UNKNOWN")

    def test_10_two_pages_require_complete_coverage(self):
        pages=[page([user(1),user(2)],number=1,per_page=2,total=3,total_pages=2),
               page([user(3,False)],number=2,per_page=2,total=3,total_pages=2)]
        s=inspect_access_pages(pages)
        self.assertEqual((s.user_count,s.authenticated_user_flags,s.pages_checked),(3,2,2))

    def test_11_incomplete_two_page_inventory_denied(self):
        self.assertDenied([page([user(1),user(2)],per_page=2,total=3,total_pages=2)])

    def test_12_pages_must_be_in_order(self):
        self.assertDenied([page([user(1)],number=2)])

    def test_13_repeated_page_1_denied(self):
        self.assertDenied([page([user(1)],number=1,per_page=1,total=2,total_pages=2),
                           page([user(2)],number=1,per_page=1,total=2,total_pages=2)])

    def test_14_changed_total_between_pages_denied(self):
        self.assertDenied([page([user(1)],number=1,per_page=1,total=2,total_pages=2),
                           page([user(2)],number=2,per_page=1,total=3,total_pages=2)])

    def test_15_changed_page_size_between_pages_denied(self):
        self.assertDenied([page([user(1)],number=1,per_page=1,total=2,total_pages=2),
                           page([user(2)],number=2,per_page=2,total=2,total_pages=1)])

    def test_16_duplicate_uuid_across_pages_denied(self):
        self.assertDenied([page([user(1)],number=1,per_page=1,total=2,total_pages=2),
                           page([user(1)],number=2,per_page=1,total=2,total_pages=2)])

    def test_17_duplicate_uuid_with_different_case_denied(self):
        first=user(0xABCDEF)
        second={**first,"id":first["id"].upper()}
        self.assertDenied([page([first,second])])

    def test_18_missing_access_flag_denied(self):
        self.assertDenied([page([{"id":uid(1)}])])

    def test_19_string_access_flag_denied(self):
        self.assertDenied([page([{**user(1),"access_seat":"true"}])])

    def test_20_integer_access_flag_denied(self):
        self.assertDenied([page([{**user(1),"access_seat":1}])])

    def test_21_missing_uuid_denied(self):
        self.assertDenied([page([{"access_seat":True}])])

    def test_22_non_uuid_identifier_denied(self):
        self.assertDenied([page([{"id":"fake","access_seat":True}])])

    def test_23_response_success_false_denied(self):
        self.assertDenied([page([user(1)],success=False)])

    def test_24_response_error_array_denied(self):
        self.assertDenied([page([user(1)],errors=[{"message":"unauthorized"}])])

    def test_25_missing_result_info_denied(self):
        p=page([user(1)])
        del p["result_info"]
        self.assertDenied([p])

    def test_26_missing_result_list_denied(self):
        p=page([user(1)])
        p["result"]=None
        self.assertDenied([p])

    def test_27_count_mismatch_denied(self):
        p=page([user(1)])
        p["result_info"]["count"]=2
        self.assertDenied([p])

    def test_28_true_is_not_valid_numeric_page(self):
        p=page([user(1)])
        p["result_info"]["page"]=True
        self.assertDenied([p])

    def test_29_zero_page_size_denied(self):
        self.assertDenied([page([user(1)],per_page=0)])

    def test_30_total_pages_mismatch_denied(self):
        self.assertDenied([page([user(1)],total_pages=2)])

    def test_31_result_total_count_mismatch_denied(self):
        self.assertDenied([page([user(1)],total=2,total_pages=1)])

    def test_32_more_than_ten_pages_denied(self):
        self.assertDenied([page([user(1)]) for _ in range(11)])

    def test_33_inventory_absent_denied(self):
        self.assertDenied(None)

    def test_34_inventory_dict_instead_of_pages_denied(self):
        self.assertDenied({"result":[]})

    def test_35_error_is_redacted_by_safe_summary(self):
        safe=inventory_summary([{"bad":"sensitive-secret"}])
        self.assertEqual(safe["status"],"UNKNOWN_INCOMPLETE_OR_INVALID")
        self.assertNotIn("sensitive",json.dumps(safe))

    def test_36_user_email_never_serialized(self):
        unsafe="alice-secret@example.invalid"
        p=page([{**user(1),"email":unsafe}])
        body=json.dumps(inventory_summary([p]))
        self.assertNotIn(unsafe,body)

    def test_37_billing_plan_is_never_attested(self):
        self.assertFalse(inventory_summary(fake(1))["plan_attested"])

    def test_38_no_automatic_deploy_from_access_inventory(self):
        self.assertIs(inventory_summary(fake(1))["automatic_deploy_allowed"],False)

    def test_39_cli_disallows_api_url_or_real_user_json(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(main(["--api-url","https://api.cloudflare.com"]),2)
        self.assertIn("NO_GO",out.getvalue())

    def test_40_cli_synthetic_self_check_only(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(main(["--synthetic-self-check"]),0)
        self.assertNotIn("@example",out.getvalue())

    def test_41_module_has_no_network_credential_or_storage_imports(self):
        source=(Path(__file__).parent/"access_seat_inventory_v080_lab.py").read_text()
        for forbidden in ["urllib.request","requests.","os.environ","Authorization: Bearer","fetch(", "open("]:
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
