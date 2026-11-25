import json,sqlite3,unittest
from v294_d1_oracle_custody import initialize,pull_once
from v295_bridge_observation import summarize
from test_v294_d1_oracle_custody import row,T

def fixture(c,delta=2):
    r=row(c)
    p=json.loads(r['raw_json'])
    p['configuration']={}
    p['snapshot'].update(confirmed=True,footprint={'available':True,'buy':10+delta,'sell':10,'delta':delta})
    r['raw_json']=json.dumps(p)
    return r

class Integration(unittest.TestCase):
    def test_receipt_to_feature_and_asof(self):
        db=sqlite3.connect(':memory:')
        try:
            initialize(db)
            a=[fixture(T),fixture(T+300000,-1),fixture(T+900000)]
            pull_once(db,lambda _:a,T,T+1000000,enabled=True)
            s=summarize(db,T,T+1000000)
            self.assertEqual((s['received'],s['valid_footprint'],s['longest_segment']),(3,3,2))
            self.assertFalse(s['prospective_admitted'])
            s=summarize(db,T,T+300000)
            self.assertEqual(s['received'],1)
        finally:
            db.close()
    def test_empty_and_window(self):
        db=sqlite3.connect(':memory:')
        try:
            initialize(db)
            self.assertEqual(summarize(db,T,T)['valid_footprint'],0)
            with self.assertRaisesRegex(ValueError,'window'):summarize(db,T,T+86400001)
        finally:
            db.close()
