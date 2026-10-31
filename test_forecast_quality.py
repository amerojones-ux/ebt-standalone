"""Synthetic control tests only. These are not sports model validation results."""
import copy
from datetime import datetime,timedelta,timezone
import unittest
from ebt_forecast_quality import (validate_prediction,chronological_split,fit_isotonic,
    calibrated_probability,calibrate_and_test,assess_release,digest,wilson_lower,scores)


def row(i=0, **kw):
    start=datetime(2024,1,1,20,tzinfo=timezone.utc)+timedelta(days=i)
    iso=lambda t:t.isoformat()
    r=dict(forecast_id=f'f{i:04}',event_id=f'e{i}',subject_id='synthetic',market='REB',
           side='under',line=10.5,period='full_game',rules_hash='fixture-rules',league='NBA',
           threshold_band='fixture-8-to-12',model_version='fixture-v1',
           selection_policy='frozen-top-one-per-game',archive_ref=f'fixture-lock/{i}',
           probability_kind='model_forecast',p_raw=.8,slate_date=start.date().isoformat(),
           event_start=iso(start),locked_at=iso(start-timedelta(hours=1)),
           generated_at=iso(start-timedelta(hours=2)),training_cutoff=iso(start-timedelta(days=1)),
           source_available_times=[iso(start-timedelta(hours=3))],
           settlement='FINAL',actual=12 if i%10==0 else 4,
           settled_at=iso(start+timedelta(hours=3)),result_ref=f'fixture-result/{i}')
    r.update(kw);return r


class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=[row(i) for i in range(400)]
        cls.report=calibrate_and_test(cls.data)

    def candidate(self, **kw):
        r=row(401)
        for k in ('official_identity_ref','official_status_ref','market_snapshot_ref','rules_ref',
                  'opportunity_model_ref','matchup_model_ref','mc1_receipt','mc2_receipt',
                  'mc3_receipt','stress_review_ref'):r[k]='synthetic-review-only'
        r.update(data_conflict=False,role_restriction_unresolved=False,
                 market_snapshot_at=r['locked_at'],official_status_at=r['locked_at'],
                 mc1_trials=250000,mc2_trials=250000,mc3_trials=250000)
        # Strip outcome labels from live research assessment input.
        for k in ('actual','settlement','settled_at','result_ref'):r.pop(k)
        r.update(kw);return r

    def decide(self,r=None,report=None,review=True):
        r=r or self.candidate();report=report or self.report
        return assess_release(r,report,asof=r['locked_at'],archive_review=
             {'report_sha256':digest(report),'review_ref':'synthetic-external-review'} if review else None)

    def test_chronological_date_and_event_separation(self):
        a,b,c=chronological_split(self.data)
        self.assertEqual([len(a),len(b),len(c)],[200,100,100])
        self.assertTrue(set(r['event_id'] for r in a).isdisjoint(r['event_id'] for r in c))
        self.assertLess(max(r['slate_date'] for r in a),min(r['slate_date'] for r in b))
    def test_duplicate_book_cannot_add_a_sample(self):
        with self.assertRaises(ValueError):chronological_split(self.data+[dict(self.data[0],platform='other')])
    def test_alternates_count_once_per_event(self):
        a,b,c=chronological_split(self.data+[dict(self.data[0],line=9.5,forecast_id='alternate')])
        self.assertEqual(len(a)+len(b)+len(c),400)
    def test_group_selection_uses_forecast_not_result(self):
        d=[dict(self.data[0],line=9.5,forecast_id='alternate',actual=0,p_raw=.7)]
        a,_,_=chronological_split(self.data+d)
        self.assertEqual(next(r for r in a if r['event_id']=='e0')['forecast_id'],'f0000')
    def test_future_feature_rejected(self):
        with self.assertRaises(ValueError):validate_prediction(row(source_available_times=[row()['event_start']]))
    def test_missing_lock_provenance_rejected(self):
        with self.assertRaises(ValueError):validate_prediction(row(archive_ref=''))
    def test_descriptive_percentage_rejected(self):
        with self.assertRaises(ValueError):validate_prediction(row(probability_kind='last_five_hit_rate'))
    def test_wrong_timezone_or_slate(self):
        for r in (row(locked_at='2024-01-01T19:00:00'),row(slate_date='2024-01-02')):
            with self.assertRaises(ValueError):validate_prediction(r)
    def test_training_cutoff_cannot_equal_generation(self):
        with self.assertRaises(ValueError):validate_prediction(row(training_cutoff=row()['generated_at']))
    def test_different_model_cannot_pool(self):
        with self.assertRaises(ValueError):chronological_split(self.data+[row(500,model_version='new')])
    def test_prior_labels_unavailable_at_calibration_lock(self):
        d=copy.deepcopy(self.data);d[0]['settled_at']=d[-1]['settled_at']
        with self.assertRaises(ValueError):chronological_split(d)
    def test_test_labels_cannot_change_fitted_calibrator(self):
        d=copy.deepcopy(self.data)
        for r in d[300:]:r['actual']=12
        self.assertEqual(calibrate_and_test(d)['calibrator'],self.report['calibrator'])
    def test_wrong_calibration_direction_pooled(self):
        m=fit_isotonic([row(0,p_raw=.2,actual=4),row(1,p_raw=.8,actual=12)])
        self.assertEqual(m['p'],[.5,.5])
    def test_ties_pooled(self):self.assertAlmostEqual(self.report['calibrator']['p'][0],.9)
    def test_extrapolation_rejected(self):
        with self.assertRaises(ValueError):calibrated_probability(self.report['calibrator'],.99)
    def test_empty_data_stays_unfit(self):
        with self.assertRaises(ValueError):calibrate_and_test([])
    def test_small_archive_holds(self):
        r=calibrate_and_test([row(i) for i in range(80)])
        self.assertEqual(r['status'],'HOLD')
    def test_cohort_bound_not_small_streak(self):self.assertLess(wilson_lower(4,4),.8)
    def test_synthetic_diagnostic_success_not_wager_approval(self):
        r=self.decide();self.assertEqual(r['status'],'PASSES_LOCAL_RESEARCH_GATE')
        self.assertFalse(r['wager_approved'])
    def test_no_review_holds(self):self.assertEqual(self.decide(review=False)['status'],'HOLD')
    def test_forged_unbound_review_holds(self):
        c=self.candidate();r=assess_release(c,self.report,asof=c['locked_at'],archive_review={'report_sha256':'wrong','review_ref':'x'})
        self.assertEqual(r['status'],'HOLD')
    def test_missing_role_evidence_holds(self):self.assertEqual(self.decide(self.candidate(opportunity_model_ref=''))['status'],'HOLD')
    def test_bad_trial_count_holds(self):self.assertEqual(self.decide(self.candidate(mc1_trials=0))['status'],'HOLD')
    def test_status_conflict_holds(self):self.assertEqual(self.decide(self.candidate(data_conflict=True))['status'],'HOLD')
    def test_stale_market_holds(self):self.assertEqual(self.decide(self.candidate(market_snapshot_at=row(401)['source_available_times'][0]))['status'],'HOLD')
    def test_future_market_holds(self):self.assertEqual(self.decide(self.candidate(market_snapshot_at=row(401)['event_start']))['status'],'HOLD')
    def test_wrong_cohort_holds(self):self.assertEqual(self.decide(self.candidate(model_version='new'))['status'],'HOLD')
    def test_used_test_event_holds(self):self.assertEqual(self.decide(self.candidate(event_id='e1'))['status'],'HOLD')
    def test_future_calibration_report_holds(self):
        r=copy.deepcopy(self.report);r['evaluated_through']='2030-01-01T00:00:00Z'
        self.assertEqual(self.decide(report=r)['status'],'HOLD')
    def test_release_does_not_look_at_outcomes(self):
        a=self.decide(self.candidate(actual=0));b=self.decide(self.candidate(actual=100))
        self.assertEqual(a,b)
    def test_scoring_winners_and_losers(self):
        self.assertAlmostEqual(scores([.8,.8],[1,0])['brier'],.34)


if __name__=='__main__':unittest.main()
