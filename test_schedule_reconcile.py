import unittest
from ebt_schedule_reconcile import reconcile_schedule
from ebt_certification import CertificationHold

class ScheduleTests(unittest.TestCase):
    def test_removed_and_changed_events_trigger_review(self):
        old={"complete":True,"capture_id":"a","retrieved_at":"2026-10-28T10:00:00Z",
             "events":[{"event_id":"1","start":"20:00"},{"event_id":"2","start":"21:00"}]}
        new={"complete":True,"capture_id":"b","retrieved_at":"2026-10-28T11:00:00Z",
             "events":[{"event_id":"2","start":"22:00"},{"event_id":"3","start":"23:00"}]}
        result=reconcile_schedule(old,new)
        self.assertEqual(result["removed"],["1"])
        self.assertEqual(result["added"],["3"])
        self.assertEqual(result["changed"],["2"])
        self.assertTrue(result["requires_manual_review"])
        self.assertFalse(result["schedule_truth_certified"])
        with self.assertRaises(CertificationHold):
            reconcile_schedule({**old,"complete":False},new)
        with self.assertRaises(CertificationHold):
            reconcile_schedule(old,{**new,"retrieved_at":"2026-10-28T09:00:00Z"})
        with self.assertRaises(CertificationHold):
            reconcile_schedule(old,{**new,"events":[{"event_id":"2"},{"event_id":"2"}]})

if __name__=="__main__":
    unittest.main()
