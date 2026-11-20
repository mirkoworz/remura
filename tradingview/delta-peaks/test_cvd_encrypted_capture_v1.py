# REMURA v0.8.181 LAB — 19/11/2026, sessione 06:46 CET
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_encrypted_capture_v1 as m
from abc_encrypted_handoff_lab_v1 import gpg,identity
from cvd_oos_protocol_preview_v2 import clock

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.a=clock("2026-11-19"); self.now=self.a+120000
    def windows(self,rows=None):
        return [{"start_ms":self.a,"end_ms":self.a,"rows":rows or []}]
    def package(self,rows=None):
        return json.loads(m.package(self.windows(rows),start=self.a,end=self.a,now=self.now,reads=1))
    def test_empty_is_not_market_coverage(self):
        p=self.package()
        self.assertEqual(p["coverage"]["missing_requested_slots"],1)
        self.assertFalse(p["outcomes_computed"])
        self.assertFalse(p["scientific_admission"])
    def test_bad_payload_retained_in_quarantine(self):
        r=dict(event_key="synthetic",received_at_ms=self.a+1,bar_close_ms=self.a,
               symbol=m.SYMBOL,timeframe="5",event_type="BAR_EVENT",version=m.VERSION,
               is_timely=0,raw_json="not json")
        p=self.package([r])
        self.assertEqual(p["quality"],"QUARANTINED_VALIDATION_FAILURE")
        self.assertEqual(p["windows"][0]["rows"],[r])
        r["symbol"]="OTHER"
        with self.assertRaises(m.AuditError):self.package([r])
    def test_cross_fold_and_bounded_scope(self):
        end=clock("2026-11-23")
        with self.assertRaises(m.AuditError):m.scope(end-m.M5,end,end+120000)
        with self.assertRaises(m.AuditError):m.scope(self.a,self.a+288*m.M5,self.a+290*m.M5)
        self.assertEqual(m.scope(end-m.M5,end-m.M5,end+120000)[1],end-1)
    def test_no_remote_without_approval(self):
        with patch.object(m,"api_request") as call:
            with self.assertRaises(m.AuditError):m.capture("","",start=self.a,end=self.a,now=self.now,home="",recipient="A"*40)
            call.assert_not_called()
    def test_capture_uses_only_test_and_cipher_receipt(self):
        reply={"success":True,"result":[{"success":True,"results":[],"meta":{"rows_read":1,"rows_written":0}}]}
        with patch.object(m,"require_account_id",return_value="x"),patch.object(m,"require_account_token",return_value="y"),patch.object(m,"api_request"),patch.object(m,"inspect_verified_inventory",return_value={m.MAIN_DB:"main",m.TEST_DB:"test"}),patch.object(m,"fetch_page",return_value=reply) as get,patch.object(m,"seal",return_value=b"cipher") as encrypt:
            cipher,receipt=m.capture("x","y",start=self.a,end=self.a,now=self.now,home="",recipient="A"*40,approved=True,guard=lambda:None)
            get.assert_called_once_with("x","test","y",self.a,self.a,self.now)
            self.assertEqual(cipher,b"cipher")
            self.assertFalse(receipt["custody_verified"])
            self.assertFalse(json.loads(encrypt.call_args.args[2])["outcomes_computed"])
            reply["result"][0]["meta"]["rows_written"]=1
            with self.assertRaises(m.AuditError):m.capture("x","y",start=self.a,end=self.a,now=self.now,home="",recipient="A"*40,approved=True,guard=lambda:None)
    def test_real_gpg_synthetic_key_roundtrip(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            recipient=identity(a,"recovery")
            pub=gpg(a,"--export",recipient).stdout
            gpg(b,"--import",data=pub)
            body=m.wire({"fixture":True})
            cipher=m.seal(b,recipient,body)
            result=gpg(a,"--status-fd","2","--decrypt","--output","-",data=cipher)
            self.assertEqual(result.stdout,body)
            self.assertIn(b"[GNUPG:] GOODMDC",result.stderr)
            with self.assertRaises(m.AuditError):m.seal(a,recipient,body)
