import unittest
from dataclasses import replace
from datetime import datetime,timezone
from trust_attestation import TrustAttestation, assess
NOW=datetime(2026,11,2,12,tzinfo=timezone.utc)
A=TrustAttestation("e1","a"*64,"WeatherAPI","OfficialLeague","reviewer-1",NOW.isoformat(),"game-1","game-1","VERIFIED")
def check(a,**kwargs):
    return assess(a,evidence_id="e1",digest="a"*64,provider="WeatherAPI",now=NOW,approved_verifiers=frozenset({"reviewer-1"}),approved_official_sources=frozenset({"OfficialLeague"}),**kwargs)[0]
class AttestationTests(unittest.TestCase):
    def test_missing(self): self.assertEqual(check(None),"HOLD")
    def test_consistent(self): self.assertEqual(check(A),"PASS")
    def test_wrong_digest(self): self.assertEqual(check(replace(A,evidence_sha256="b"*64)),"FAIL")
    def test_wrong_provider(self): self.assertEqual(check(replace(A,provider="Sportradar")),"FAIL")
    def test_unknown_reviewer(self): self.assertEqual(check(replace(A,verifier_id="unknown")),"HOLD")
    def test_unknown_official(self): self.assertEqual(check(replace(A,official_source="Unknown")),"HOLD")
    def test_unmatched_event(self): self.assertEqual(check(replace(A,official_event_id="game-2")),"HOLD")
    def test_unverified(self): self.assertEqual(check(replace(A,status="PENDING")),"HOLD")
if __name__=="__main__": unittest.main()
