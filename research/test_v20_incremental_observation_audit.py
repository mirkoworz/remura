"""New-only tests for V20 post-checkpoint audit; never contact providers."""
import json
import tempfile
import unittest
from pathlib import Path
from v20_incremental_observation_audit import build_report, utc

S='2026-11-22T22:25:00Z'
T='2026-11-23T05:35:00Z'


def sample(t, l=50, other=1):
    return {'t':t, 'lPct':l, 'sPct':100-l, 'lLots':other, 'sLots':3}


class IncrementalAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pub = Path(self.tmp.name)/'pub'; self.pub.mkdir()
        self.private = Path(self.tmp.name)/'private'; self.private.mkdir()

    def tearDown(self): self.tmp.cleanup()

    def file(self, folder, name, records):
        (folder/f'{name}.json').write_text(json.dumps({'symbol':name,'records':records}))

    def test_public_delta_and_real_change_of_payload(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z',59),sample('2026-11-23T02:55:17Z',51)])
        o=build_report(self.pub,S,T)['myfxbook_retail_public']
        self.assertEqual((o['series_updated_after_checkpoint'],o['changed_long_pct_since_checkpoint']), (1,1))
        self.assertEqual(o['largest_public_long_pp_changes'][0]['delta_long_pp'],-8)

    def test_pct_unchanged_but_other_payload_changed(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z',85),sample('2026-11-23T02:55:17Z',85,other=2)])
        o=build_report(self.pub,S,T)['myfxbook_retail_public']
        self.assertEqual(o['unchanged_long_pct_since_checkpoint'],1)
        self.assertEqual(o['changed_payload_since_checkpoint'],1)

    def test_old_series_marked_stale(self):
        self.file(self.pub,'US500',[sample('2026-10-22T01:38:06Z')])
        o=build_report(self.pub,S,T)['myfxbook_retail_public']
        self.assertEqual(o['no_new_checkpoint_records'],1)
        self.assertEqual(o['stale_public_series'],['US500'])

    def test_private_symbol_never_in_json_output(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z'),sample('2026-11-23T02:55:17Z')])
        self.file(self.private,'SECRET_NAME',[sample('2026-11-22T20:45:11Z'),sample('2026-11-23T02:53:02Z',75)])
        result=build_report(self.pub,S,T,self.private)
        s=json.dumps(result['capital_demo_aggregate_only'])
        self.assertNotIn('SECRET_NAME',s)
        self.assertNotIn('75',s)
        self.assertNotIn('private',s)
        self.assertEqual(result['capital_demo_aggregate_only']['changed_long_direction_counts']['increased'],1)

    def test_future_snapshot_rejected(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z'),sample('2026-11-24T02:55:17Z')])
        with self.assertRaisesRegex(ValueError,'Future'): build_report(self.pub,S,T)

    def test_duplicate_snapshot_rejected(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z'),sample('2026-11-22T22:23:40Z')])
        with self.assertRaisesRegex(ValueError,'Non-monotonic'): build_report(self.pub,S,T)

    def test_absent_baseline_fail_closed(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-23T02:55:17Z')])
        with self.assertRaisesRegex(ValueError,'Missing baseline'): build_report(self.pub,S,T)

    def test_percentages_and_utc_cutoffs_validated(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z',-1)])
        with self.assertRaisesRegex(ValueError,'Invalid sentiment'): build_report(self.pub,S,T)
        with self.assertRaisesRegex(ValueError,'UTC'): utc('2026-11-22T22:25:00')
        with self.assertRaisesRegex(ValueError,'follow'): build_report(self.pub,T,S)

    def test_forward_only_multiple_records_since_checkpoint(self):
        self.file(self.pub,'EURUSD',[sample('2026-11-22T22:23:40Z',40),sample('2026-11-23T02:55:17Z',60),sample('2026-11-23T04:55:17Z',70)])
        o=build_report(self.pub,S,T)['myfxbook_retail_public']
        self.assertEqual(o['new_records_retained_after_checkpoint'],2)
        self.assertEqual(o['largest_public_long_pp_changes'][0]['delta_long_pp'],30)


if __name__ == '__main__': unittest.main()
