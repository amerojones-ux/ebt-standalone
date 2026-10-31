import contextlib,io,json,pathlib,tempfile,unittest
from ebt_validation import probability,evaluate_holdout,validate_chain
from ebt_cli import main,strict_json
from test_validation import valid,q

class PrecisionAndCLI(unittest.TestCase):
    def test_cutoff_must_not_round_up(self):
        for key,value in [('calibrated_p','0.86999999999999999999'),('lower_bound','0.79999999999999999999')]:
            r=valid();r[key]=value
            self.assertEqual(q(r)['forecast'],'HOLD')
    def test_probability_bounds_before_float_conversion(self):
        for value in ('1.00000000000000000001','-0.00000000000000000001'):
            with self.assertRaises(ValueError):probability(value)
    def test_positive_ev_without_binary_rounding(self):
        r=valid();r.update(win_p='.9',push_p='0',loss_p='.1')
        # This exact finite decimal yields a small positive EV; float arithmetic loses it.
        r['quote']['decimal_odds']='1.11111111111111111112'
        self.assertTrue(q(r)['conditional_wager_gate_passed'])
        self.assertEqual(q(r)['wager'],'NOT APPROVED')
        r['quote']['decimal_odds']='1.11111111111111111111'
        self.assertEqual(q(r)['wager'],'NOT APPROVED')
        self.assertFalse(q(r)['conditional_wager_gate_passed'])
    def test_probability_mass_must_reconcile(self):
        r=valid();r['loss_p']='0.10000000001'
        self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_json_duplicates_and_nonfinite(self):
        for text in ('{"p":0.1,"p":0.9}','{"p":NaN}','{"p":Infinity}'):
            with self.assertRaises(ValueError):strict_json(text)
    def test_cli_missing_forecast_is_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'input.json';p.write_text('[{}]');output=io.StringIO()
            with contextlib.redirect_stdout(output):
                rc=main(['qualify',str(p),'--now','2026-10-28T18:01:00Z','--max-quote-age-seconds','120'])
            self.assertEqual(rc,0);self.assertEqual(json.loads(output.getvalue())['results'][0]['forecast'],'HOLD')
    def test_cli_invalid_json_returns_machine_readable_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'input.json';p.write_text('[{"calibrated_p":0.1,"calibrated_p":0.9}]');output=io.StringIO()
            with contextlib.redirect_stdout(output):
                rc=main(['qualify',str(p),'--now','2026-10-28T18:01:00Z','--max-quote-age-seconds','120'])
            self.assertEqual(rc,2);self.assertEqual(json.loads(output.getvalue())['status'],'HOLD')
    def test_holdout_requires_identity(self):
        with self.assertRaises(ValueError):evaluate_holdout([{'forecast_id':''}])
        with self.assertRaises(ValueError):evaluate_holdout([None])
    def test_ledger_invalid_identity(self):
        for record in ({'id':''},None,{'id':[]}):
            with self.assertRaises(ValueError):validate_chain([record])
if __name__=='__main__':unittest.main(verbosity=2)
