import unittest
from omega_v8.research import (Candidate,rank_beneficiaries,hurdle_survival,
    bayesian_zero_posterior,correlated_combo_sim,scenario_mc,backtest,immutable_audit_record)

def candidate(name,share=.3,**kwargs):
    return Candidate(name,"A","REB",30,12,share,.7,True,**kwargs)

class OmegaV8Tests(unittest.TestCase):
    def test_beneficiary_rank(self):
        self.assertEqual(rank_beneficiaries([candidate("B",.2),candidate("A",.4)])[0]["player"],"A")
    def test_injury_hold(self):
        self.assertEqual(rank_beneficiaries([candidate("A",injury_status="QUESTIONABLE")])[0]["status"],"HOLD")
    def test_zero_event(self):
        self.assertAlmostEqual(hurdle_survival(1,.2,2),.8)
        self.assertAlmostEqual(bayesian_zero_posterior(0,8),2/18)
    def test_combo_pairing(self):
        self.assertEqual(correlated_combo_sim([10],[0],10,100),1.)
    def test_joint_opportunity(self):
        result=scenario_mc([candidate("A",.3),candidate("B",.4)],2,1000)
        self.assertEqual(result["status"],"RESEARCH_ONLY")
        self.assertLessEqual(result["adverse"]["A"],1.)
    def test_no_share_overallocation(self):
        with self.assertRaises(ValueError):
            scenario_mc([candidate("A",.8),candidate("B",.5)],2,100)
    def test_temporal_backtest(self):
        row={"issued_at":"2026-01-01","event_at":"2026-01-02","settled_at":"2026-01-03","probability":.8,"outcome":1}
        self.assertAlmostEqual(backtest([row])["brier"],.04)
    def test_audit_hash(self):
        a=immutable_audit_record("genesis",{"id":"x"},{"outcome":"HIT"})
        self.assertEqual(len(a["sha256"]),64)

if __name__=="__main__": unittest.main()
