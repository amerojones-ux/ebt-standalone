import hashlib
import tempfile
import unittest
from pathlib import Path
from ebt_certification import CertificationHold
from ebt_evidence_link import (verify_identity_evidence,
                               verify_availability_evidence,
                               verify_historical_evidence)

class EvidenceLinkTests(unittest.TestCase):
    def test_linked_capture_integrity_without_truth_claim(self):
        with tempfile.TemporaryDirectory() as d:
            index = {}
            for name,host,time in (("feature","www.teamrankings.com","2026-10-28T09:00:00Z"),
                                   ("identity","official.nba.com","2026-10-28T09:00:00Z"),
                                   ("availability","official.nba.com","2026-10-28T09:00:00Z"),
                                   ("outcome","official.nba.com","2026-10-29T02:00:00Z")):
                body = name.encode()
                Path(d,name).write_bytes(body)
                index[name]={"sha256":hashlib.sha256(body).hexdigest(),
                             "url":"https://"+host+"/test",
                             "retrieved_at":time,"raw_path":name}
            hosts={"www.teamrankings.com","official.nba.com"}
            event={"event_id":"g","team_ids":["a","b"]}
            player={"player_id":"p","team_id":"a","event_id":"g",
                    "identity_corrob":True,"corroboration_capture_ids":["feature","identity"]}
            result=verify_identity_evidence(event,player,index,d,
                cutoff="2026-10-28T10:00:00Z",allowed_hosts=hosts)
            self.assertFalse(result["identity_truth_certified"])
            report={"official_verified":True,"status":"available","capture_id":"availability",
                    "published_at":"2026-10-28T08:59:00Z",
                    "retrieved_at":"2026-10-28T09:00:00Z"}
            result=verify_availability_evidence(report,index,d,
                cutoff="2026-10-28T10:00:00Z",max_age_seconds=7200,allowed_hosts=hosts)
            self.assertFalse(result["availability_truth_certified"])
            history={"event_id":"g","player_id":"p","team_id":"a",
                "market_definition":"points >= 10","threshold":"10",
                "source_capture_ids":["feature"],"outcome_capture_id":"outcome",
                "model_version":"synthetic","outcome_source":"official",
                "feature_asof":"2026-10-28T09:00:00Z",
                "prediction_created_at":"2026-10-28T10:00:00Z",
                "scheduled_start":"2026-10-28T23:00:00Z",
                "outcome_final_at":"2026-10-29T02:00:00Z",
                "certification_status":"independently_reviewed","outcome_verified":True}
            result=verify_historical_evidence(history,index,d,
                cutoff="2026-10-29T03:00:00Z",allowed_hosts=hosts)
            self.assertFalse(result["historical_truth_certified"])
            history["outcome_capture_id"]="feature"
            with self.assertRaises(CertificationHold):
                verify_historical_evidence(history,index,d,
                    cutoff="2026-10-29T03:00:00Z",allowed_hosts=hosts)
            index["availability"]["url"]="https://www.teamrankings.com/test"
            with self.assertRaises(CertificationHold):
                verify_availability_evidence(report,index,d,
                    cutoff="2026-10-28T10:00:00Z",max_age_seconds=7200,allowed_hosts=hosts)

if __name__=="__main__":
    unittest.main()
