import contextlib,copy,hashlib,io,json,pathlib,tempfile,unittest,urllib.error
from fractions import Fraction
from ebt_collect import collect,extract,tr_table,nba_scoreboard,verify_extraction,source_kind,NBA_URL
from ebt_calibration import assessment,calibrated_probability
from ebt_cli import main

TR_URL='https://www.teamrankings.com/nba/stat/test-metric?date=2026-10-28'
HTML=b'<h1>SYNTHETIC fixture</h1><table><tr><th>Rank</th><th>Team</th><th>2026</th></tr><tr><td>1</td><td><a href="/nba/team/fixture-a">Fixture A</a></td><td>39.1</td></tr><tr><td>2</td><td><a href="/nba/team/fixture-b">Fixture B</a></td><td>38.2</td></tr></table>'
PARAM=dict(expected_heading='SYNTHETIC fixture',column='2026',expected_rows=2)
SCOPE=dict(competition='TEST',market='PTS',threshold_type='GE',model_version='SYNTHETIC')
POLICY=dict(version='test-only',min_training_rows=2,min_validation_rows=2,min_training_events=2,min_validation_events=2)

def row(i,p,result,test=False):
    day='2026-10-28' if test else '2026-10-26'
    return dict(SCOPE,forecast_id=str(i),event_id='event-'+str(i),certified=True,p=p,result=result,training_end='2026-10-25T00:00:00Z',issued_at=day+'T10:00:00Z',event_start=day+'T12:00:00Z',outcome_available_at=day+'T15:00:00Z')
def run_assessment(train=None,test=None,**changes):
    args=dict(scope=SCOPE,fit_at='2026-10-27T00:00:00Z',assessed_at='2026-10-29T00:00:00Z',policy=POLICY);args.update(changes)
    return assessment(train if train is not None else [row(1,'.1','HIT'),row(2,'.2','MISS'),row(3,'.3','HIT')],test if test is not None else [row(4,'.15','HIT',True),row(5,'.4','MISS',True)],**args)

class CollectionTests(unittest.TestCase):
    def test_capture_and_extraction_are_bound(self):
        def fetch(url,timeout,max_bytes):return (b'User-agent: *\nDisallow:\n','text/plain') if url.endswith('robots.txt') else (HTML,'text/html')
        with tempfile.TemporaryDirectory() as d:
            receipt=collect(TR_URL,d,_fetch=fetch);self.assertEqual(receipt['status'],'COLLECTED')
            claim=extract(receipt,d,parameters=PARAM);self.assertEqual(claim['extracted']['rows'][0]['value'],'39.1');self.assertTrue(verify_extraction(receipt,d,claim))
            self.assertFalse(verify_extraction(receipt,d,claim,{**PARAM,'column':'2025'}))
            claim['extracted']['rows'][0]['value']='99';self.assertFalse(verify_extraction(receipt,d,claim))
            (pathlib.Path(d)/receipt['raw_path']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):extract(receipt,d,parameters=PARAM)
    def test_http_denial_is_hold_without_retry(self):
        calls=[]
        def fetch(url,*args):calls.append(url);raise urllib.error.HTTPError(url,403,'Forbidden',{},None)
        with tempfile.TemporaryDirectory() as d:self.assertEqual(collect(TR_URL,d,_fetch=fetch)['status'],'HOLD')
        self.assertEqual(len(calls),1)
    def test_robots_denial_stops_content_request(self):
        calls=[]
        def fetch(url,*args):calls.append(url);return b'User-agent: *\nDisallow: /\n','text/plain'
        with tempfile.TemporaryDirectory() as d:self.assertEqual(collect(TR_URL,d,_fetch=fetch)['status'],'HOLD')
        self.assertEqual(len(calls),1)
    def test_robots_rate_directive_requires_scheduler(self):
        def fetch(url,*args):return b'User-agent: *\nCrawl-delay: 10\n','text/plain'
        with tempfile.TemporaryDirectory() as d:self.assertIn('scheduler',collect(TR_URL,d,_fetch=fetch)['reason'])
    def test_unapproved_url_is_rejected(self):
        for url in ('http://www.teamrankings.com/nba/stat/x?date=2026-10-28','https://evil.example/data','https://www.teamrankings.com/nba/stat/x?date=bad','https://user:secret@www.teamrankings.com/nba/stat/x?date=2026-10-28'):
            with self.assertRaises(ValueError):source_kind(url)
    def test_table_column_and_scope_must_match(self):
        for kwargs in ({**PARAM,'column':'2025'},{**PARAM,'expected_heading':'wrong'},{**PARAM,'expected_rows':30}):
            with self.assertRaises(ValueError):tr_table(HTML,**kwargs)
    def test_missing_stat_is_not_zero(self):
        with self.assertRaises(ArithmeticError):tr_table(HTML.replace(b'39.1',b'--'),**PARAM)
    def test_duplicate_table_does_not_pick_favorable_one(self):
        with self.assertRaises(ValueError):tr_table(HTML+HTML.split(b'</h1>')[1],**PARAM)
    def test_nba_identity_and_date(self):
        game={'gameId':'0000000001','gameStatus':1,'homeTeam':{'teamId':1},'awayTeam':{'teamId':2},'gameTimeUTC':'2026-10-28T23:00:00Z'}
        board={'scoreboard':{'gameDate':'2026-10-28','leagueId':'00','games':[game]}}
        self.assertEqual(nba_scoreboard(json.dumps(board).encode(),expected_date='2026-10-28')['games'][0]['event_id'],'0000000001')
        with self.assertRaises(ValueError):nba_scoreboard(json.dumps(board).encode(),expected_date='2026-10-29')
        board['scoreboard']['games'].append(game)
        with self.assertRaises(ValueError):nba_scoreboard(json.dumps(board).encode(),expected_date='2026-10-28')

class CalibrationTests(unittest.TestCase):
    def test_isotonic_pooling_and_unapproved_result(self):
        result=run_assessment();self.assertEqual(result['status'],'RESEARCH_FIT_EVALUATED');self.assertFalse(result['calibration_certified']);self.assertFalse(result['forecast_approved'])
        self.assertEqual(calibrated_probability(result['blocks'],'.15'),Fraction(1,2));self.assertEqual(calibrated_probability(result['blocks'],'.9'),1)
    def test_insufficient_data_is_hold(self):self.assertEqual(run_assessment(train=[])['status'],'HOLD')
    def test_future_training_outcomes_are_rejected(self):
        train=[row(1,'.1','HIT'),row(2,'.2','MISS')];train[0]['outcome_available_at']='2026-10-28T00:00:00Z';self.assertEqual(run_assessment(train=train)['status'],'HOLD')
    def test_validation_cannot_predate_fit(self):
        test=[row(4,'.1','HIT'),row(5,'.2','MISS')];self.assertEqual(run_assessment(test=test)['status'],'HOLD')
    def test_same_event_cannot_cross_split(self):
        test=[row(4,'.1','HIT',True),row(5,'.2','MISS',True)];test[0]['event_id']='event-1';self.assertEqual(run_assessment(test=test)['status'],'HOLD')
    def test_scope_and_certification_are_required(self):
        for field,value in [('market','OTHER'),('certified',False),('result','PENDING')]:
            train=[row(1,'.1','HIT'),row(2,'.2','MISS')];train[0][field]=value;self.assertEqual(run_assessment(train=train)['status'],'HOLD')
    def test_no_weight_retune_from_failed_holdout(self):
        result=run_assessment();self.assertIsNone(result['heldout_calibrated']['log_loss']);self.assertTrue(result['heldout_calibrated']['log_loss_infinite']);self.assertFalse(result['calibration_certified'])
    def test_group_counts_matter(self):
        train=[row(1,'.1','HIT'),row(2,'.2','MISS')];train[1]['event_id']='event-1';self.assertEqual(run_assessment(train=train)['status'],'HOLD')
    def test_cli_temporal_fit_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);train=[row(1,'.1','HIT'),row(2,'.2','MISS')];test=[row(4,'.15','HIT',True),row(5,'.4','MISS',True)]
            settings=dict(scope=SCOPE,fit_at='2026-10-27T00:00:00Z',assessed_at='2026-10-29T00:00:00Z',policy=POLICY)
            for name,obj in [('train.json',train),('test.json',test),('settings.json',settings)]: (root/name).write_text(json.dumps(obj))
            output=io.StringIO()
            with contextlib.redirect_stdout(output):rc=main(['calibrate',str(root/'train.json'),'--validation',str(root/'test.json'),'--settings',str(root/'settings.json')])
            self.assertEqual(rc,0);report=json.loads(output.getvalue());self.assertEqual(report['status'],'RESEARCH_FIT_EVALUATED');self.assertFalse(report['calibration_certified'])
if __name__=='__main__':unittest.main(verbosity=2)
