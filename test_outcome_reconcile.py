import unittest
from ebt_outcome_reconcile import reconcile_outcomes
from ebt_certification import CertificationHold

def prediction(i, direction="over",threshold=10):
    return {"event_id":str(i),"player_id":"p","market":"points",
            "direction":direction,"threshold":threshold,
            "issued_at":"2026-10-28T10:00:00Z",
            "scheduled_start":"2026-10-28T23:00:00Z"}
def final(i,value=12,status="final"):
    return {"event_id":str(i),"player_id":"p","market":"points",
            "status":status,"value":value,"capture_id":"official-fixture",
            "reported_at":"2026-10-29T02:00:00Z"}

class OutcomeTests(unittest.TestCase):
    def test_all_outcome_classes(self):
        predictions=[prediction(1),prediction(2),prediction(3),
                     prediction(4),prediction(5),prediction(6,"under")]
        finals=[final(1,12),final(2,9),final(3,10),final(4,status="postponed"),
                final(6,8)]
        result=reconcile_outcomes(predictions,finals,cutoff="2026-10-29T03:00:00Z")
        self.assertEqual([x["result"] for x in result["results"]],
                         ["HIT","MISS","PUSH","VOID","PENDING","HIT"])
        self.assertFalse(result["all_finalized"])
        self.assertFalse(result["independently_verified"])
    def test_reject_duplicate_and_post_cutoff(self):
        with self.assertRaises(CertificationHold):
            reconcile_outcomes([prediction(1)],[final(1),final(1)],
                               cutoff="2026-10-29T03:00:00Z")
        with self.assertRaises(CertificationHold):
            reconcile_outcomes([prediction(1)],[final(1)],
                               cutoff="2026-10-29T01:00:00Z")
if __name__=="__main__":
    unittest.main()
