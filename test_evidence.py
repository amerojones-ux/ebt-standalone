import contextlib,copy,hashlib,io,json,pathlib,tempfile,unittest
from unittest.mock import patch
from ebt_evidence import ingest,validate_record,field_key
from ebt_cli import main

# All source domains and captures in this module are synthetic fixtures.
POLICY={'version':'1.0','competitions':{'TEST':{'official':['league.example'],'teamrankings':['stats.example'],'secondary':['secondary.example']}}}

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.addCleanup(self.tmp.cleanup)
        raw=b'SYNTHETIC FIXTURE: active player';(self.root/'capture.txt').write_bytes(raw)
        self.record=dict(schema_version='1.0',record_id='one',source_id='league-report',competition='TEST',event_id='event-1',subject_kind='player',subject_id='player-1',fact='participation',metric='game_status',window='CURRENT',snapshot_kind='LIVE',source_kind='official',source_url='https://league.example/report',retrieved_at='2026-10-28T18:00:00Z',effective_at='2026-10-28T17:59:00Z',published_at='2026-10-28T17:59:00Z',value='ACTIVE',raw_path='capture.txt',raw_sha256=hashlib.sha256(raw).hexdigest())
        self.kw=dict(raw_root=self.root,cutoff='2026-10-28T18:01:00Z',max_age_seconds=180,policy=POLICY)
        self.requirement={k:self.record[k] for k in ('competition','event_id','subject_kind','subject_id','fact','metric','window','snapshot_kind')}
    def run_ingest(self,rows=None,req=None):return ingest(rows if rows is not None else [self.record],req if req is not None else [self.requirement],**self.kw)
    def test_valid_capture_remains_research(self):
        r=self.run_ingest();self.assertEqual(r['fields'][0]['verdict'],'RESEARCH_INPUT');self.assertFalse(r['source_truth_verified']);self.assertFalse(r['forecast_approved'])
    def test_spoofed_domain(self):
        self.record['source_url']='https://league.example.evil.test/report';self.assertEqual(self.run_ingest()['fields'][0]['verdict'],'HOLD')
    def test_credentials_in_url(self):
        self.record['source_url']='https://user:secret@league.example/report';self.assertTrue(self.run_ingest()['rejected_records'])
    def test_raw_hash_mismatch(self):
        self.record['raw_sha256']='0'*64;self.assertTrue(self.run_ingest()['rejected_records'])
    def test_path_traversal(self):
        self.record['raw_path']='../capture.txt';self.assertTrue(self.run_ingest()['rejected_records'])
    def test_absolute_capture_path(self):
        self.record['raw_path']=str(self.root/'capture.txt');self.assertTrue(self.run_ingest()['rejected_records'])
    def test_future_source_timestamps(self):
        for key in ('effective_at','published_at','retrieved_at'):
            with self.subTest(key=key):
                r=copy.deepcopy(self.record);r[key]='2026-10-29T00:00:00Z';self.assertTrue(self.run_ingest([r])['rejected_records'])
    def test_naive_timestamp(self):
        self.record['effective_at']='2026-10-28T17:59:00';self.assertTrue(self.run_ingest()['rejected_records'])
    def test_old_evidence_reread_now(self):
        self.record['effective_at']='2026-10-28T16:00:00Z';self.assertTrue(self.run_ingest()['rejected_records'])
    def test_history_cannot_clear_active_status(self):
        self.record['snapshot_kind']='HISTORICAL';self.assertEqual(self.run_ingest()['fields'][0]['verdict'],'HOLD')
    def test_secondary_cannot_clear_participation(self):
        self.record.update(source_kind='secondary',source_url='https://secondary.example/report');self.assertEqual(self.run_ingest()['fields'][0]['verdict'],'HOLD')
    def test_out_rejects_even_if_secondary_active(self):
        s=copy.deepcopy(self.record);s.update(record_id='two',source_id='other',source_kind='secondary',source_url='https://secondary.example/report');self.record['value']='OUT';self.assertEqual(self.run_ingest([self.record,s])['fields'][0]['verdict'],'REJECT')
    def test_conflicting_current_sources_hold(self):
        s=copy.deepcopy(self.record);s.update(record_id='two',source_id='other',source_kind='secondary',source_url='https://secondary.example/report',value='QUESTIONABLE');r=self.run_ingest([self.record,s]);self.assertTrue(r['fields'][0]['conflict']);self.assertEqual(r['fields'][0]['verdict'],'HOLD')
    def test_new_snapshot_supersedes_same_source(self):
        old=copy.deepcopy(self.record);old.update(record_id='old',effective_at='2026-10-28T17:58:00Z',value='OUT');r=self.run_ingest([old,self.record]);self.assertEqual(r['fields'][0]['verdict'],'RESEARCH_INPUT');self.assertEqual(len(r['records']),2)
    def test_missing_required_field(self):
        req=copy.deepcopy(self.requirement);req['event_id']='event-2';self.assertEqual(self.run_ingest(req=[req])['fields'][0]['verdict'],'HOLD')
    def test_duplicate_records_do_not_pass(self):
        self.assertEqual(self.run_ingest([self.record,self.record])['fields'][0]['verdict'],'HOLD')
    def test_duplicate_id_holds_both_fields(self):
        other=copy.deepcopy(self.record);other['subject_id']='player-2';req={k:other[k] for k in self.requirement}
        result=self.run_ingest([self.record,other],[self.requirement,req]);self.assertTrue(all(r['verdict']=='HOLD' for r in result['fields']))
    def test_malformed_record_id(self):
        self.record['record_id']=[];self.assertTrue(self.run_ingest()['rejected_records'])
    def test_missing_subject_id(self):
        self.record['subject_id']='';self.assertTrue(self.run_ingest()['rejected_records'])
    def test_no_implicit_policy_or_coverage(self):
        with self.assertRaises(ValueError):self.run_ingest(req=[])
        self.record['competition']='UNSUPPORTED';self.assertTrue(self.run_ingest()['rejected_records'])
    def test_numeric_metric_and_units(self):
        r=copy.deepcopy(self.record);r.update(subject_kind='team',subject_id='team-1',fact='team_stat',metric='opp_3pa',window='SEASON',source_kind='teamrankings',source_url='https://stats.example/report',value='39.1',unit='attempts_per_100_possessions',sample_size=4,window_start='2026-10-20T00:00:00Z',window_end='2026-10-28T00:00:00Z')
        req={k:r[k] for k in self.requirement};self.assertEqual(self.run_ingest([r],[req])['fields'][0]['verdict'],'RESEARCH_INPUT')
        s=copy.deepcopy(r);s.update(record_id='two',source_id='second',unit='attempts_per_game');self.assertEqual(self.run_ingest([r,s],[req])['fields'][0]['verdict'],'HOLD')
    def test_shared_capture_hashed_once_per_batch(self):
        other=copy.deepcopy(self.record);other.update(record_id='two',source_id='other')
        read=pathlib.Path.read_bytes
        with patch.object(pathlib.Path,'read_bytes',autospec=True,side_effect=read) as reader:
            report=self.run_ingest([self.record,other]);self.assertEqual(reader.call_count,1)
        self.assertEqual(report['fields'][0]['verdict'],'RESEARCH_INPUT')
        self.assertEqual(report['valid_records'],2);self.assertEqual(report['unique_valid_capture_hashes'],1)
    def test_new_snapshot_replaces_older_same_time_conflict(self):
        a=copy.deepcopy(self.record);b=copy.deepcopy(self.record)
        a.update(record_id='a',effective_at='2026-10-28T17:58:00Z',value='OUT');b.update(record_id='b',effective_at='2026-10-28T17:58:00Z',value='QUESTIONABLE')
        self.assertEqual(self.run_ingest([a,b,self.record])['fields'][0]['verdict'],'RESEARCH_INPUT')
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as other:
            outside=pathlib.Path(other)/'raw';outside.write_text('outside');(self.root/'escape').symlink_to(outside);self.record['raw_path']='escape'
            self.assertTrue(self.run_ingest()['rejected_records'])
    def test_bad_policy_fails_clearly(self):
        self.kw['policy']={'version':'1.0','competitions':{'TEST':[]}}
        with self.assertRaises(ValueError):self.run_ingest()
    def test_cli_end_to_end(self):
        for name,obj in [('records.json',[self.record]),('requirements.json',[self.requirement]),('policy.json',POLICY)]: (self.root/name).write_text(json.dumps(obj))
        output=io.StringIO()
        with contextlib.redirect_stdout(output):rc=main(['evidence',str(self.root/'records.json'),'--requirements',str(self.root/'requirements.json'),'--raw-root',str(self.root),'--cutoff',self.kw['cutoff'],'--max-age-seconds','180','--policy',str(self.root/'policy.json')])
        self.assertEqual(rc,0);self.assertFalse(json.loads(output.getvalue())['forecast_approved'])
if __name__=='__main__':unittest.main(verbosity=2)
