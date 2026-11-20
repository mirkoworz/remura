# REMURA Experience v0.19 LAB — 20/11/2026 CET
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from snapshot_store_v019 import SnapshotStore, stamp_ms

STAMP='2026-11-20T16:00:00Z'
NOW=stamp_ms(STAMP)
OWNER=lambda:{'role':'OWNER','subject':'owner','generation':'fixture-v019'}
USER=lambda:{'role':'CONTRIBUTOR','subject':'a','generation':'fixture-v019'}
CLOCK=lambda:NOW
YES=lambda p,d:True

def data():
    return {'as_of':STAMP,'prices':[{'instrument':'EURUSD','price':1.25,'source':'FIXTURE_PRICE','observed_at':STAMP}], 'forex_rows':[{'dataset':'TFF_FIXTURE','code':'099741','report_date':'2026-11-17','first_seen_at':STAMP,'oi':1000,'asset_long':300,'asset_short':100,'leveraged_long':100,'leveraged_short':300}]}

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.f=SnapshotStore(Path(self.tmp.name)/'fixture');self.f.initialize_snapshot()
    def tearDown(self):self.tmp.cleanup()
    def pub(self,**kw):
        return self.f.publish_snapshot(**(dict(expected=0,data=data(),auth=OWNER,approve=YES,clock=CLOCK)|kw))
    def view(self,auth=USER,clock=CLOCK):
        r=self.f.deliver(auth,clock)
        return None if r is None else json.loads(r['body'])
    def seed(self):self.assertEqual(self.pub(),'PUBLISHED')
    def test_empty(self):self.assertIsNone(self.view())
    def test_cot_catalog(self):
        self.seed();v=self.view();self.assertEqual(len(v['cot']),28)
        p=next(r for r in v['cot'] if r['pair']=='EURUSD');self.assertEqual((p['asset_gap'],p['leveraged_gap']),(20,-20))
        self.assertEqual(next(r for r in v['cot'] if r['pair']=='EURJPY')['status'],'UNAVAILABLE')
        self.assertFalse(v['scientific_admission']);self.assertEqual(v['sentiment'],{'myfxbook':'UNAVAILABLE','capital':'UNAVAILABLE'})
    def test_price_exact_and_reopen(self):
        self.seed();self.f=SnapshotStore(self.f.root);self.assertEqual(self.view()['prices'][0]['price'],1.25)
    def test_invalid_price_source(self):
        x=data();x['prices'][0]['source']='real';self.assertEqual(self.pub(data=x),'BLOCKED');self.assertIsNone(self.view())
    def test_invalid_cot(self):
        x=data();x['forex_rows'][0]['oi']=0;self.assertEqual(self.pub(data=x),'BLOCKED')
    def test_duplicate_contract(self):
        x=data();x['forex_rows']*=2;self.assertEqual(self.pub(data=x),'BLOCKED')
    def test_unknown_field(self):
        x=data();x['prices'][0]['secret']='fixture';self.assertEqual(self.pub(data=x),'BLOCKED')
    def test_expired_publish(self):self.assertEqual(self.pub(clock=lambda:NOW+900001),'BLOCKED')
    def test_expired_delivery(self):self.seed();self.assertIsNone(self.view(clock=lambda:NOW+900001))
    def test_stale_price_flag(self):
        x=data();x['prices'][0]['observed_at']='2026-11-20T15:00:00Z';self.assertEqual(self.pub(data=x),'PUBLISHED');self.assertEqual(self.view()['prices'][0]['freshness'],'STALE')
    def test_approval_binds_digest(self):
        self.assertEqual(self.pub(approve=lambda p,d:len(d)==64 and p[0]==0),'PUBLISHED')
    def test_approval_denial(self):self.assertEqual(self.pub(approve=lambda p,d:False),'BLOCKED');self.assertIsNone(self.view())
    def test_roles(self):self.assertEqual(self.pub(auth=USER),'BLOCKED');self.seed();self.assertIsNone(self.view(OWNER))
    def test_subject_swap(self):
        self.seed();a=iter([USER(),USER(),dict(USER(),subject='b')]);self.assertIsNone(self.view(auth=lambda:next(a)))
    def test_clock_changes_at_delivery(self):
        self.seed();a=iter([NOW,NOW+1]);self.assertIsNone(self.view(clock=lambda:next(a)))
    def test_revision_and_duplicate(self):
        self.seed();self.assertEqual(self.pub(),'BLOCKED');x=data();x['prices'][0]['price']=1.5;self.assertEqual(self.pub(expected=1,data=x),'PUBLISHED');self.assertEqual(self.view()['revision'],2)
    def test_rollback_both(self):
        self.seed();paths=(self.f.archive,self.f.chain)
        for p in paths:shutil.copy2(p,p.with_suffix('.bak'))
        self.assertEqual(self.pub(expected=1),'PUBLISHED')
        for p in paths:shutil.copy2(p.with_suffix('.bak'),p)
        self.assertIsNone(self.view())
    def test_archive_tamper(self):
        self.seed()
        with sqlite3.connect(self.f.archive) as a:
            a.execute('DROP TRIGGER fixture_revision_no_update');a.execute("UPDATE fixture_revision SET payload='{}'")
        self.assertIsNone(self.view())
    def test_interruption(self):
        for stage in ['archive','journal']:
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as p:
                self.f=SnapshotStore(Path(p)/'f');self.f.initialize_snapshot();self.assertEqual(self.pub(interrupt=stage),'INTERRUPTED');self.assertIsNone(self.view());self.assertEqual(self.pub(),'BLOCKED')
    def test_no_raw_interface(self):self.seed();self.assertIsNone(self.f.read(USER));self.assertEqual(self.f.publish(0,STAMP,1,OWNER),'BLOCKED')
    def test_wrong_generation(self):self.seed();self.assertIsNone(self.view(auth=lambda:dict(USER(),generation='old')))
    def test_adapter_failure(self):
        def broken():raise RuntimeError('synthetic')
        self.assertEqual(self.pub(auth=broken),'BLOCKED');self.assertIsNone(self.view(auth=broken))

if __name__=='__main__':unittest.main()
