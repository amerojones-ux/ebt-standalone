import unittest,copy
from ebt_validation import *

def valid():
    r={k:True for k in EVIDENCE};r.update(issued_at='2026-10-28T18:00:00Z',model_locked_at='2026-10-28T17:59:00Z',event_start='2026-10-28T23:00:00Z',calibration_training_end='2026-10-27T00:00:00Z',calibrated_p=.90,lower_bound=.82,central_cushion=3,adverse_cushion=1,market_key='SYNTHETIC|GE|6',settlement_rules_verified=True,win_p=.90,push_p=0,loss_p=.10)
    r['runs']={k:dict(trials=100000,hits=90000,input_sha256='a'*64,code_sha256='b'*64,seed=1) for k in ('baseline','adversarial','scenario')}
    r['quote']=dict(operator_verified=True,market_key=r['market_key'],quoted_at='2026-10-28T18:00:00Z',retrieved_at='2026-10-28T18:00:00Z',decimal_odds=1.2)
    return r
def q(r):return qualify(r,now='2026-10-28T18:01:00Z',max_quote_age_seconds=120)
class Tests(unittest.TestCase):
    def test_inclusive_boundary(self):self.assertEqual(settle(6,6,'GE',final=True,participated=True),'HIT')
    def test_strict_boundary(self):
        for c in ('GT','LT'):self.assertEqual(settle(6,6,c,final=True,participated=True),'PUSH')
    def test_dnp_requires_rules(self):
        self.assertEqual(settle(None,6,'GE',final=True,participated=False),'PENDING')
        self.assertEqual(settle(None,6,'GE',final=True,participated=False,void_rule_verified=True),'VOID')
    def test_pending_and_under(self):
        self.assertEqual(settle(5,6,'LT',final=True,participated=True),'HIT')
        self.assertEqual(settle(5,6,'GE',final=False,participated=True),'PENDING')
    def test_nan(self):
        with self.assertRaises(ValueError):probability(float('nan'))
    def test_zero_cushion(self):self.assertIsNone(cushion(2,0,'OVER')['relative'])
    def test_complete_gate_synthetic(self):
        r=q(valid());self.assertEqual(r['wager'],'NOT APPROVED')
        self.assertTrue(r['conditional_wager_gate_passed'])
        self.assertFalse(r['independent_source_verification_performed'])
    def test_evidence_fails_closed(self):
        for k in EVIDENCE:
            r=valid();r[k]='true';self.assertEqual(q(r)['forecast'],'HOLD',k)
    def test_out_kills(self):
        r=valid();r['official_out']=True;self.assertEqual(q(r)['forecast'],'REJECT')
    def test_missing_runs(self):
        r=valid();del r['runs']['scenario'];self.assertEqual(q(r)['forecast'],'HOLD')
    def test_fake_trials_and_hash(self):
        for x in (99999,True,100000.0):
            r=valid();r['runs']['baseline']['trials']=x;self.assertEqual(q(r)['forecast'],'HOLD')
        r=valid();r['runs']['baseline']['input_sha256']='x'*64;self.assertEqual(q(r)['forecast'],'HOLD')
    def test_stale_or_future_quote(self):
        for t in ('2026-10-28T17:00:00Z','2026-10-28T18:02:00Z'):
            r=valid();r['quote']['retrieved_at']=t;self.assertEqual(q(r)['wager'],'NOT APPROVED');self.assertTrue(q(r)['conditional_forecast_gate_passed'])
    def test_market_identity(self):
        r=valid();r['quote']['market_key']='OTHER';self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_ev(self):
        r=valid();r['quote']['decimal_odds']=1.05;self.assertEqual(q(r)['wager'],'NOT APPROVED')
    def test_calibration_gate(self):
        for k,v in [('calibrated_p',.86),('lower_bound',.79),('calibration_training_end','2026-10-29T00:00:00Z')]:
            r=valid();r[k]=v;self.assertEqual(q(r)['forecast'],'HOLD')
    def test_timezone(self):
        self.assertEqual(clock('2026-10-28T13:00:00-05:00'),clock('2026-10-28T18:00:00Z'))
        with self.assertRaises(ValueError):clock('2026-10-28T18:00:00')
    def test_temporal_holdout(self):
        r=dict(forecast_id='synthetic-1',certified=True,training_end='2026-10-27T00:00:00Z',issued_at='2026-10-28T18:00:00Z',event_start='2026-10-28T23:00:00Z',outcome_available_at='2026-10-29T02:00:00Z',result='HIT',p=.8)
        self.assertAlmostEqual(evaluate_holdout([r])['brier'],.04)
        with self.assertRaises(ValueError):evaluate_holdout([r,r])
        r['training_end']=r['issued_at']
        with self.assertRaises(ValueError):evaluate_holdout([r])
    def test_chain_tamper(self):
        r=dict(id='synthetic-1',previous_sha256='0'*64,payload={'status':'HOLD'});r['sha256']=record_hash(r)
        self.assertEqual(validate_chain([r]),r['sha256'])
        r['payload']['status']='APPROVED'
        with self.assertRaises(ValueError):validate_chain([r])
if __name__=='__main__':unittest.main(verbosity=2)
