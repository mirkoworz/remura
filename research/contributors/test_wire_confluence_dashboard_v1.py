# REMURA Contributors v0.37 LAB — 16/11/2026 16:33 CET
import unittest
from copy import deepcopy
from test_explicit_pine_wire_lab_v1 import payload,ms
from test_explicit_level_contract_lab_v1 import man,meta
from test_level_confluence_v1 import ASOF,REC,FUTURE
from explicit_pine_wire_lab_v1 import CONFIG_ID,handoff
from confluence_dashboard_v1 import wire_report

def report(m=None,p=None,receipt=REC):
    manual=[dict(man(),config_id=CONFIG_ID)] if m is None else m
    automatic=[{"payload":payload() if p is None else p,"received_ms":ms(receipt)}]
    out=wire_report(manual,automatic,asof_utc=ASOF,synthetic=True)
    assert out["result"]==handoff(manual,automatic,asof_utc=ASOF,synthetic=True)
    return out["html"]

class WireReportTests(unittest.TestCase):
    def test_candidate_and_provenance(self):
        page=report()
        for term in ("v0.37 LAB","SOLO DATI SINTETICI","confluenza candidata",CONFIG_ID,
                     "Automatici confrontati: 1","Coppie vicine candidate: 1","nessun segnale operativo"):
            self.assertIn(term,page)
    def test_distant_not_missing(self):
        page=report(p=payload(price="1.08600"))
        self.assertIn("Distante: 1",page)
        self.assertIn("Automatici confrontati: 1",page)
        self.assertNotIn("confronto di prezzo non eseguito",page)
    def test_late_not_distant(self):
        page=report(receipt=FUTURE)
        self.assertIn("Automatici tardivi: 1",page)
        self.assertIn("confronto di prezzo non eseguito",page)
        self.assertNotIn("Distante: 1",page)
    def test_missing_and_incompatible_manual(self):
        self.assertIn("nessun manuale confrontabile",report(m=[]))
        item=dict(man(provider="FXCM"),config_id=CONFIG_ID)
        self.assertIn("Manuali con metadati non ammessi: 1",report(m=[item]))
    def test_late_review(self):
        item=dict(man(),config_id=CONFIG_ID)
        item["entry"]["history"][0]["at_utc"]=FUTURE
        self.assertIn("Manuali esclusi dalla revisione: 1",report(m=[item]))
    def test_privacy_and_nonmutation(self):
        item=dict(man(),config_id=CONFIG_ID)
        item["entry"]["data"]["note"]="private-secret"
        before=deepcopy(item)
        page=report(m=[item])
        self.assertEqual(item,before)
        for term in ("private-secret","friend-a","1.08530","1.08540","auto-1","<script"):
            self.assertNotIn(term,page)
    def test_opt_in_and_unknown_schema(self):
        with self.assertRaises(ValueError):wire_report([],[],asof_utc=ASOF)
        with self.assertRaises(ValueError):report(p=payload(schema="unexpected"))
