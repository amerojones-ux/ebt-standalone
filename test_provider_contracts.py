import unittest
from datetime import datetime, timezone, timedelta
from dataclasses import replace
from provider_contracts import Contract, Capture, verify
NOW=datetime(2026,11,1,12,tzinfo=timezone.utc)
C=Contract('api.example','events',{'event_id':str,'count':int},3600)
E=Capture('api.example','events',200,{'event_id':'e1','count':3},NOW.isoformat(),NOW.isoformat(),'official-e1')
def check(e=E,c=C,ids=frozenset({'official-e1'})):
    return verify(c,e,now=NOW,reconciled_ids=ids)
class Tests(unittest.TestCase):
    def test_pass(self): self.assertEqual(check()[0],'PASS')
    def test_missing(self): self.assertEqual(check(None)[0],'NOT_TESTED')
    def test_host(self): self.assertEqual(check(replace(E,host='other'))[0],'FAIL')
    def test_endpoint(self): self.assertEqual(check(replace(E,endpoint='other'))[0],'FAIL')
    def test_auth(self): self.assertEqual(check(replace(E,status=403))[0],'FAIL')
    def test_rate(self): self.assertEqual(check(replace(E,status=429))[0],'HOLD')
    def test_null(self): self.assertEqual(check(replace(E,body={'event_id':None,'count':3}))[0],'FAIL')
    def test_bool_not_int(self): self.assertEqual(check(replace(E,body={'event_id':'e1','count':True}))[0],'FAIL')
    def test_empty(self): self.assertEqual(check(replace(E,body={'event_id':' ','count':3}))[0],'FAIL')
    def test_stale(self): self.assertEqual(check(replace(E,published_at=(NOW-timedelta(days=1)).isoformat()))[0],'HOLD')
    def test_future(self): self.assertEqual(check(replace(E,retrieved_at=(NOW+timedelta(seconds=1)).isoformat()))[0],'HOLD')
    def test_provenance(self): self.assertEqual(check(ids=frozenset())[0],'HOLD')
    def test_naive(self): self.assertEqual(check(replace(E,published_at='2026-11-01T12:00:00'))[0],'HOLD')

    def test_server_error(self): self.assertEqual(check(replace(E,status=503))[0],'HOLD')
    def test_not_found(self): self.assertEqual(check(replace(E,status=404))[0],'HOLD')
    def test_invalid_body(self): self.assertEqual(check(replace(E,body=None))[0],'FAIL')
    def test_missing_field(self): self.assertEqual(check(replace(E,body={'event_id':'e1'}))[0],'FAIL')
    def test_bad_published_time(self): self.assertEqual(check(replace(E,published_at='not-a-date'))[0],'HOLD')
    def test_published_after_retrieval(self):
        self.assertEqual(check(replace(E,published_at=NOW.isoformat(),retrieved_at=(NOW-timedelta(seconds=1)).isoformat()))[0],'HOLD')
    def test_refetch_does_not_refresh_source(self):
        self.assertEqual(check(replace(E,published_at=(NOW-timedelta(days=1)).isoformat(),retrieved_at=NOW.isoformat()))[0],'HOLD')

if __name__=='__main__': unittest.main()
