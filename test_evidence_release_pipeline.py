import unittest
from datetime import datetime, timezone
from dataclasses import replace
from provider_contracts import Contract, Capture
from provider_capture_integrity import CaptureRecord, canonical_digest
from provider_intake import ProviderIntake
from evidence_release_pipeline import EvidenceBundle, verify_bundle

NOW=datetime(2026,11,1,12,tzinfo=timezone.utc)
TIME=NOW.isoformat()
PAYLOAD={"event_id":"e1","count":3}
C=Contract("api.example","events",{"event_id":str,"count":int},3600)
E=Capture("api.example","events",200,PAYLOAD,TIME,TIME,"official-e1")
R=CaptureRecord("WeatherAPI","events",TIME,TIME,PAYLOAD,canonical_digest(PAYLOAD))
I=ProviderIntake("WeatherAPI","api.example","events","v1",True,True,True,True,True,"official-e1")
B=EvidenceBundle(C,E,R,I)
def run(bundle): return verify_bundle(bundle,now=NOW,reconciled_ids=frozenset({"official-e1"}))
class PipelineTests(unittest.TestCase):
    def test_consistent(self): self.assertEqual(run(B)[0],"PASS")
    def test_payload_mismatch(self):
        r=replace(R,payload={"event_id":"e2","count":3},sha256=canonical_digest({"event_id":"e2","count":3}))
        self.assertEqual(run(replace(B,integrity_record=r))[0],"HOLD")
    def test_identity_mismatch(self):
        self.assertEqual(run(replace(B,intake=replace(I,api_host="other")))[0],"HOLD")
    def test_timestamp_mismatch(self):
        self.assertEqual(run(replace(B,integrity_record=replace(R,retrieved_at="2026-11-01T11:00:00Z")))[0],"HOLD")
    def test_unverified_source(self):
        self.assertEqual(run(replace(B,intake=replace(I,source_authenticated=None)))[0],"HOLD")
    def test_invalid_digest(self):
        self.assertEqual(run(replace(B,integrity_record=replace(R,sha256="0"*64)))[0],"HOLD")
    def test_provider_identity_mismatch(self):
        self.assertEqual(run(replace(B,integrity_record=replace(R,provider="Sportradar")))[0],"HOLD")
    def test_endpoint_identity_mismatch(self):
        self.assertEqual(run(replace(B,integrity_record=replace(R,endpoint_id="other")))[0],"HOLD")
    def test_publication_timestamp_mismatch(self):
        self.assertEqual(run(replace(B,integrity_record=replace(R,source_published_at="2026-11-01T11:00:00Z")))[0],"HOLD")
    def test_evidence_reference_mismatch(self):
        self.assertEqual(run(replace(B,intake=replace(I,evidence_id="different")))[0],"HOLD")
    def test_official_reconciliation_unverified(self):
        self.assertEqual(run(replace(B,intake=replace(I,official_reconciled=None)))[0],"HOLD")
    def test_source_authentication_explicit_failure(self):
        self.assertEqual(run(replace(B,intake=replace(I,source_authenticated=False)))[0],"HOLD")
if __name__=="__main__": unittest.main()
