import contextlib,io,json,pathlib,tempfile,unittest
from decimal import Decimal
from ebt_cli import main,strict_json,archive_report
from ebt_validation import evaluate_holdout
from test_validation import valid,q

class DataIntegrity(unittest.TestCase):
    def test_json_retains_qualification_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'input.json';raw=json.dumps([valid()]).replace('"calibrated_p": 0.9','"calibrated_p": 0.86999999999999999999');p.write_text(raw);output=io.StringIO()
            with contextlib.redirect_stdout(output):main(['qualify',str(p),'--now','2026-10-28T18:01:00Z','--max-quote-age-seconds','120'])
            self.assertEqual(json.loads(output.getvalue())['results'][0]['forecast'],'HOLD')
    def test_decimal_json_tokens_preserved(self):
        self.assertEqual(strict_json('{"p":0.86999999999999999999}')['p'],Decimal('0.86999999999999999999'))
    def test_rereading_an_old_quote_does_not_refresh_it(self):
        r=valid();r['quote']['quoted_at']='2026-10-28T17:00:00Z';r['quote']['retrieved_at']='2026-10-28T18:00:00Z';self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_missing_quote_effective_time(self):
        r=valid();r['quote'].pop('quoted_at',None);self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_quote_cannot_be_published_after_retrieval(self):
        r=valid();r['quote']['quoted_at']='2026-10-28T18:00:30Z';self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_duplicate_and_ragged_csv(self):
        header='date,card_version,selection,threshold,rechecked_result,source_primary'
        texts=[header+',threshold\n2026-10-27,A,Test,6+,HIT,url,7+\n',header+'\n2026-10-27,A,Test,6+,HIT\n',header+'\n2026-10-27,A,Test,6+,HIT,url,extra\n']
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'input.csv'
            for t in texts:
                p.write_text(t)
                with self.assertRaises(ValueError):archive_report(p)
    def test_extreme_but_nonzero_probability_has_finite_log_loss(self):
        row=dict(forecast_id='synthetic',certified=True,training_end='2026-10-27T00:00:00Z',issued_at='2026-10-28T18:00:00Z',event_start='2026-10-28T23:00:00Z',outcome_available_at='2026-10-29T02:00:00Z',result='HIT',p='1e-400')
        self.assertAlmostEqual(evaluate_holdout([row])['log_loss'],400*__import__('math').log(10))
        row.update(result='MISS',p='0.99999999999999999999')
        self.assertAlmostEqual(evaluate_holdout([row])['log_loss'],20*__import__('math').log(10))
if __name__=='__main__':unittest.main(verbosity=2)
