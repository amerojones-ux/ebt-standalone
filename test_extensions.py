"""Synthetic-only extensions tests: no external data or approval claims."""
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from extensions.underperformance import evaluate_count_under, audit_locked_unders
from extensions.streak_intelligence import import_authorized_streak, summarize_streak
from extensions.monte_carlo import three_way_under_mc


class UnderTests(unittest.TestCase):
    def test_half_integer_threshold(self):
        r=evaluate_count_under({'9':'0.6','10':'0.2','11':'0.2'},'10.5')
        self.assertAlmostEqual(r['market_under_probability_modeled'],.8)
        self.assertEqual(r['push_probability_modeled'],0)
        self.assertEqual(r['forecast_status'],'HOLD')
    def test_whole_line_push_distinct(self):
        r=evaluate_count_under({'9':'.6','10':'.2','11':'.2'},10)
        self.assertAlmostEqual(r['market_under_probability_modeled'],.6)
        self.assertAlmostEqual(r['push_probability_modeled'],.2)
    def test_below_normal_not_market_under(self):
        r=evaluate_count_under({'4':'.1','10':'.6','15':'.3'},9.5,normal_baseline=14,severe_fraction='.5')
        self.assertAlmostEqual(r['market_under_probability_modeled'],.1)
        self.assertAlmostEqual(r['below_normal_probability_modeled'],.7)
        self.assertAlmostEqual(r['severe_underperformance_probability_modeled'],.1)
    def test_adversarial_recovery(self):
        r=evaluate_count_under({'4':'.8','12':'.2'},10.5,over_friendly_pmf={'4':'.3','12':'.7'})
        self.assertAlmostEqual(r['over_friendly_recovery_under_probability_modeled'],.3)
        self.assertEqual(r['simulation_status'],'NOT RUN')
    def test_pmf_incomplete(self):
        with self.assertRaises(ValueError):evaluate_count_under({'4':'.9'},10.5)
    def test_negative_outcome(self):
        with self.assertRaises(ValueError):evaluate_count_under({-1:1},10.5)
    def test_ambiguous_zero_prefix(self):
        with self.assertRaises(ValueError):evaluate_count_under({'01':1},10.5)
    def test_bool(self):
        with self.assertRaises(ValueError):evaluate_count_under({'1':1},True)
    def test_nonfinite(self):
        with self.assertRaises(ValueError):evaluate_count_under({'1':'NaN'},10.5)
    def test_reject_wrong_severe_fraction(self):
        with self.assertRaises(ValueError):evaluate_count_under({'1':1},10.5,normal_baseline=3,severe_fraction=1)
    def test_all_still_hold(self):
        r=evaluate_count_under({'5':1},12.5)
        self.assertFalse(r['source_verified']);self.assertFalse(r['calibration_verified'])
        self.assertEqual(r['wager_status'],'NOT APPROVED')
    def test_locked_audit_split(self):
        base={'forecast_id':'f1','event_id':'e1','player_id':'p1','stat':'rebounds','line':9.5,'locked_at':'2026-10-01T15:00:00Z','event_start':'2026-10-01T16:00:00Z','source_available_times':['2026-10-01T14:00:00Z'],'p_under':.7,'settlement':'FINAL','result_verified':True,'actual':8}
        pending={**base,'forecast_id':'f2','settlement':'PENDING'}
        r=audit_locked_unders([base,pending])
        self.assertEqual(r['n_settled_verified'],1);self.assertEqual(r['n_pending_or_void'],1)
        self.assertFalse(r['certified_calibration'])
    def test_no_hindsight(self):
        x={'forecast_id':'f1','event_id':'e1','player_id':'p1','stat':'rebounds','line':9.5,'locked_at':'2026-10-01T15:00:00Z','event_start':'2026-10-01T16:00:00Z','source_available_times':['2026-10-01T17:00:00Z'],'p_under':.7,'settlement':'FINAL','actual':8,'result_verified':True}
        with self.assertRaises(ValueError):audit_locked_unders([x])
    def test_no_unverified_result(self):
        x={'forecast_id':'f1','event_id':'e1','player_id':'p1','stat':'rebounds','line':9.5,'locked_at':'2026-10-01T15:00:00Z','event_start':'2026-10-01T16:00:00Z','source_available_times':['2026-10-01T14:00:00Z'],'p_under':.7,'settlement':'FINAL','actual':8,'result_verified':False}
        r=audit_locked_unders([x]);self.assertEqual(r['n_pending_or_void'],1);self.assertIsNone(r['brier'])


class MonteCarloTests(unittest.TestCase):
    def test_run_and_reproduce(self):
        pmfs={'baseline':{'5':'.6','12':'.4'},'adversarial':{'5':'.2','12':'.8'},'scenario':{'5':'.4','12':'.6'}}
        seeds={'baseline':100,'adversarial':200,'scenario':300}
        a=three_way_under_mc(pmfs,10.5,trials=100000,seeds=seeds)
        b=three_way_under_mc(pmfs,10.5,trials=100000,seeds=seeds)
        self.assertEqual(a['runs'],b['runs'])
        self.assertEqual(a['runs']['baseline']['trials'],100000)
        self.assertGreater(a['runs']['baseline']['hits'],a['runs']['adversarial']['hits'])
        self.assertFalse(a['calibration_verified'])
        self.assertFalse(a['joint_parlay_test_performed'])
    def test_insufficient_runs_rejected(self):
        with self.assertRaises(ValueError):three_way_under_mc({'baseline':{5:1}},10.5,trials=99999,seeds={'baseline':1})
    def test_same_seed_rejected(self):
        with self.assertRaises(ValueError):three_way_under_mc({'baseline':{5:1},'adversarial':{5:1},'scenario':{5:1}},10.5,seeds={'baseline':1,'adversarial':1,'scenario':2})
    def test_corrupt_input_rejected(self):
        with self.assertRaises(ValueError):three_way_under_mc({'baseline':{5:1},'adversarial':{5:1},'scenario':{5:'.9'}},10.5,seeds={'baseline':1,'adversarial':2,'scenario':3})


class StreakTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.csv=root/'feed.csv';self.manifest=root/'manifest.json'
        now=datetime.now(timezone.utc).replace(microsecond=0)
        self.asof=now.isoformat();self.game=(now-timedelta(days=2)).date().isoformat()
        self.approval={'provider':'ContractedVendor','license_reference':'contract-1','approved_by':'operator',
                       'approved_at_utc':(now-timedelta(days=10)).isoformat(),'valid_until_utc':(now+timedelta(days=10)).isoformat(),
                       'permitted_use':'sports_betting_analytics','contract_reference':'document-on-file'}
        self.row={'provider':'ContractedVendor','license_reference':'contract-1','player_id':'p1','game_id':'game-A',
                  'game_date':self.game,'stat':'rebounds','value':'9','participated':'true','source_url':'https://example.org/e1',
                  'retrieved_at_utc':(now-timedelta(days=1)).isoformat(),'game_status':'FINAL'}
        self.write()
    def tearDown(self):self.tmp.cleanup()
    def write(self,rows=None):
        self.manifest.write_text(json.dumps(self.approval))
        with self.csv.open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=list(self.row));writer.writeheader();writer.writerows(rows if rows is not None else [self.row])
    def run_import(self):
        return import_authorized_streak(self.csv,approval_path=self.manifest,player_id='p1',stat='rebounds',threshold=8,
                                        operator='ge',as_of_utc=self.asof)
    def test_valid_research_streak(self):
        r=self.run_import();self.assertEqual(r['consecutive_hits'],1)
        self.assertTrue(r['historical_only']);self.assertFalse(r['rights_independently_verified'])
        self.assertIsNone(r['calibrated_next_event_probability'])
    def test_license_disallowed(self):
        self.approval['permitted_use']='media_only';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_unauthorized_nba_claim(self):
        self.approval['provider']=self.row['provider']='nba.com';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_expired_manifest(self):
        self.approval['valid_until_utc']='2020-01-01T00:00:00Z';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_mixed_vendor(self):
        self.row['provider']='Other';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_nonfinal(self):
        self.row['game_status']='LIVE';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_unknown_game(self):
        self.row['game_id']='UNKNOWN';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_duplicate_game(self):
        self.write([self.row,self.row])
        with self.assertRaises(ValueError):self.run_import()
    def test_future_retrieval(self):
        self.row['retrieved_at_utc']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat();self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_bad_url_credentials(self):
        self.row['source_url']='https://user:pass@example.org/e1';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_bad_number(self):
        self.row['value']='NaN';self.write()
        with self.assertRaises(ValueError):self.run_import()
    def test_duplicate_csv_header(self):
        self.csv.write_text('provider,provider,game_id\nx,y,z\n')
        with self.assertRaises(ValueError):self.run_import()
    def test_duplicate_manifest_key(self):
        self.manifest.write_text('{"provider":"x","provider":"y"}')
        with self.assertRaises(ValueError):self.run_import()
    def test_dnp_exclusion_and_push(self):
        rows=[{'game_id':'a','value':5,'participated':True},{'game_id':'b','value':4,'participated':False},
              {'game_id':'c','value':6,'participated':True}]
        r=summarize_streak(rows,5,'gt')
        self.assertEqual(r['consecutive_hits'],0)
        self.assertEqual(r['l5']['pushes'],1)
        self.assertEqual(r['l5']['games'],2)
    def test_inclusive_equals_hit(self):
        r=summarize_streak([{'game_id':'a','value':5,'participated':True}],5,'ge')
        self.assertEqual(r['l5']['hits'],1)
    def test_under_stat(self):
        r=summarize_streak([{'game_id':'a','value':4,'participated':True}],5,'lt')
        self.assertEqual(r['l5']['hits'],1)


class CLITests(unittest.TestCase):
    def test_under_file_cli(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'input.json';path.write_text(json.dumps({'pmf':{'8':.6,'10':.4},'line':9.5}))
            result=subprocess.run([sys.executable,'ebt_extensions_cli.py','under',str(path)],cwd=Path(__file__).parent,
                                  text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            data=json.loads(result.stdout);self.assertEqual(data['wager_status'],'NOT APPROVED')
    def test_unknown_field_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'input.json';path.write_text(json.dumps({'pmf':{'8':1},'line':9.5,'approved':True}))
            result=subprocess.run([sys.executable,'ebt_extensions_cli.py','under',str(path)],cwd=Path(__file__).parent,
                                  text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads(result.stdout)['status'],'HOLD')

if __name__=='__main__':unittest.main()