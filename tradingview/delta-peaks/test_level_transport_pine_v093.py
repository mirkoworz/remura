# REMURA v0.8.111 LAB — 16/11/2026 17:39 CET
import unittest,re
from pathlib import Path
P=Path(__file__).resolve().parent
A=(P/"REMURA-ALL-IN-ONE-Premium-v0.9.2-LEVEL-CONTRACT-PREVIEW.pine").read_text()
B=(P/"REMURA-ALL-IN-ONE-Premium-v0.9.3-LEVEL-TRANSPORT-PREVIEW.pine").read_text()
class TransportPineTests(unittest.TestCase):
    def test_calculation_body_unchanged(self):
        a=A.split("// PARAMETRI",1)[1].split("// Log-only separate cohort.",1)[0]
        b=B.split("// PARAMETRI",1)[1].split("// Separate transport candidate.",1)[0]
        self.assertEqual(a.replace("CVD LAB v0.9.2","CVD LAB v0.9.3").strip(),b.strip())
    def test_two_optins_and_window(self):
        for term in ('probeRealtime = input.bool(false','probeSend = input.bool(false',
            'probeStart = input.time(0','probeEnd = input.time(0','probeEnd - probeStart <= 3600000',
            'time_close > probeStart and time_close <= probeEnd','probeCount < 12',
            'probeChart and barstate.isconfirmed and barstate.isrealtime'):
            self.assertIn(term,B)
        self.assertEqual(len(re.findall(r"\balert\s*\(",B)),1)
        self.assertIn("if probeSend\n        alert(envelope, alert.freq_once_per_bar_close)",B)
    def test_contract_and_no_endpoint(self):
        for term in ("remura.tv.level.transport.preview.v1","0.9.3-level-preview","REALTIME_WEBHOOK_PREVIEW"):
            self.assertIn(term,B)
        self.assertNotIn("HISTORICAL_RECONSTRUCTION",B)
        self.assertNotRegex(B,r"https?://")
        self.assertEqual(len(re.findall(r"=\s*request\.footprint\(",B)),1)
if __name__=="__main__":unittest.main()
