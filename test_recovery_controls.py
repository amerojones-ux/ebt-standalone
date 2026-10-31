"""Synthetic regression cases for failures discovered in the October 30 audit."""
import unittest
from extensions.underperformance import audit_locked_unders,validated_pmf,quantile
from ebt_calibration import assessment
from test_collect_calibration import row,SCOPE,POLICY
from test_validation import valid,q


class RecoveryControls(unittest.TestCase):
    def under(self):
        return dict(forecast_id='f',event_id='e',player_id='p',stat='rebounds',line=9.5,
          locked_at='2024-01-01T18:00:00Z',event_start='2024-01-01T19:00:00Z',
          source_available_times=['2024-01-01T17:00:00Z'],p_under=.8,
          probability_kind='model_forecast',actual=4,settlement='FINAL',result_verified=True)
    def test_distinct_forecast_ids_cannot_duplicate_outcome(self):
        r=self.under()
        with self.assertRaises(ValueError):audit_locked_unders([r,dict(r,forecast_id='different',platform='other')])
    def test_probability_kind_must_be_explicit(self):
        r=self.under();r.pop('probability_kind')
        with self.assertRaises(ValueError):audit_locked_unders([r])
    def test_descriptive_rate_rejected(self):
        with self.assertRaises(ValueError):audit_locked_unders([dict(self.under(),probability_kind='L5_rate')])
    def test_zero_mass_quantile_boundary(self):self.assertEqual(quantile(validated_pmf({'0':0,'1':1}),'0.00000000000001'),1)
    def test_gate_assertions_cannot_approve(self):
        r=q(valid());self.assertEqual(r['wager'],'NOT APPROVED')
        self.assertNotIn('VALIDATED',r['forecast'])
    def test_same_event_cannot_inflate_existing_calibrator(self):
        train=[row(1,'.1','HIT'),row(2,'.2','MISS')];train[1]['event_id']=train[0]['event_id']
        policy={**POLICY,'min_training_events':2}
        r=assessment(train,[row(3,'.1','HIT',True),row(4,'.2','MISS',True)],scope=SCOPE,
            fit_at='2026-10-27T00:00:00Z',assessed_at='2026-10-29T00:00:00Z',policy=policy)
        self.assertEqual(r['status'],'HOLD')


if __name__=='__main__':unittest.main()
