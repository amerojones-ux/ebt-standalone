import unittest,tempfile,pathlib,json
from ebt_validation import *
from ebt_cli import archive_report
from test_validation import valid,q

class Regressions(unittest.TestCase):
    def test_malformed_nested_records(self):
        for field,value in [('runs',None),('quote',None),('event_start',123),('market_key',None)]:
            r=valid();r[field]=value;self.assertNotEqual(q(r)['wager'],'APPROVED')
        self.assertEqual(q(None)['forecast'],'HOLD')
    def test_numeric_overflow(self):
        r=valid();r['quote']['decimal_odds']='1e9999';self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_empty_market_key(self):
        r=valid();r['market_key']=r['quote']['market_key']='';self.assertEqual(q(r)['forecast'],'HOLD')
    def test_training_after_lock(self):
        r=valid();r['calibration_training_end']='2026-10-28T17:59:30Z';self.assertEqual(q(r)['forecast'],'HOLD')
    def test_bool_quote_policy(self):
        with self.assertRaises(ValueError):qualify(valid(),now='2026-10-28T18:01:00Z',max_quote_age_seconds=True)
    def test_append_preserves_prefix_and_rejects_stale(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'ledger.jsonl';h=append_record(p,'one',{'x':1},expected_last_sha256='0'*64);before=p.read_bytes()
            h2=append_record(p,'two',{'x':2},expected_last_sha256=h);self.assertTrue(p.read_bytes().startswith(before))
            self.assertEqual(validate_chain([json.loads(x) for x in p.read_text().splitlines()]),h2)
            after=p.read_bytes()
            with self.assertRaises(ValueError):append_record(p,'three',{},expected_last_sha256=h)
            self.assertEqual(p.read_bytes(),after)
    def test_ledger_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'ledger';h=append_record(p,'one',{},expected_last_sha256='0'*64);p.write_text('')
            with self.assertRaises(ValueError):append_record(p,'two',{},expected_last_sha256=h)
    def test_partial_tail(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'ledger';p.write_text('{')
            with self.assertRaises(ValueError):append_record(p,'one',{},expected_last_sha256='0'*64)
            self.assertEqual(p.read_text(),'{')
    def test_archive_claims_remain_uncertified(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'input.csv';p.write_text('date,card_version,selection,threshold,rechecked_result,source_primary\n2026-10-27,A,Test,6+,HIT,https://example.test\n')
            r=archive_report(p);self.assertIsNone(r['certified_hit_rate']);self.assertFalse(r['independent_outcome_verification_performed'])
    def test_impossible_outcome_log_loss(self):
        r=dict(forecast_id='one',certified=True,training_end='2026-10-27T00:00:00Z',issued_at='2026-10-28T18:00:00Z',event_start='2026-10-28T23:00:00Z',outcome_available_at='2026-10-29T02:00:00Z',result='MISS',p=1)
        self.assertTrue(__import__('math').isinf(evaluate_holdout([r])['log_loss']))
if __name__=='__main__':unittest.main(verbosity=2)
