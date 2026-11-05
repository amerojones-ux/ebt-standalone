import unittest
from datetime import datetime,timedelta,timezone
from omega_v8.validation import chronological_split,calibration_bins,verify_audit_chain
from omega_v8.research import immutable_audit_record

class ValidationTests(unittest.TestCase):
    def rows(self):
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        return [{"issued_at":(base+timedelta(days=i*3)).isoformat(),
                 "event_at":(base+timedelta(days=i*3+1)).isoformat(),
                 "settled_at":(base+timedelta(days=i*3+2)).isoformat(),
                 "probability":.7,"outcome":i%2} for i in range(10)]
    def test_split(self):
        a,b,c=chronological_split(self.rows())
        self.assertEqual((len(a),len(b),len(c)),(6,2,2))
    def test_reject_leakage(self):
        rows=self.rows()
        rows[5]["settled_at"]=rows[6]["issued_at"]
        with self.assertRaises(ValueError): chronological_split(rows)
    def test_bins(self):
        b=calibration_bins(self.rows())
        self.assertEqual(sum(x["n"] for x in b),10)
    def test_chain_tampering(self):
        a=immutable_audit_record("genesis",{"id":"1"},{"outcome":"HIT"})
        b=immutable_audit_record(a["sha256"],{"id":"2"},{"outcome":"MISS"})
        self.assertTrue(verify_audit_chain([a,b]))
        b["payload"]["settlement"]["outcome"]="HIT"
        self.assertFalse(verify_audit_chain([a,b]))

if __name__=="__main__":unittest.main()
