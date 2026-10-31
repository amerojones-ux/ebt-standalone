import contextlib,io,json,tempfile,unittest
from pathlib import Path
from ebt_json import strict_json
from ebt_quality_cli import main
from ebt_forecast_quality import digest
import test_forecast_quality as fixtures


class QualityCLI(unittest.TestCase):
    def test_report_digest_survives_exact_json_decode(self):
        v={'x':[.8,.9],'n':10,'value':.000001}
        self.assertEqual(digest(v),digest(strict_json(json.dumps(v))))
    def test_empty_archive_holds(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'empty.json';f.write_text('[]');out=io.StringIO()
            with contextlib.redirect_stdout(out):rc=main(['calibrate',str(f)])
            self.assertEqual(rc,2);self.assertEqual(json.loads(out.getvalue())['status'],'HOLD')
    def test_calibrate_assess_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);f=root/'archive.json';f.write_text(json.dumps([fixtures.row(i) for i in range(400)]))
            out=io.StringIO()
            with contextlib.redirect_stdout(out):rc=main(['calibrate',str(f)])
            self.assertEqual(rc,0)
            report=json.loads(out.getvalue());(root/'report.json').write_text(out.getvalue())
            c=fixtures.QualityTests().candidate();(root/'candidate.json').write_text(json.dumps(c))
            (root/'review.json').write_text(json.dumps({'report_sha256':digest(report),'review_ref':'synthetic-review'}))
            result=io.StringIO()
            with contextlib.redirect_stdout(result):rc=main(['assess',str(root/'candidate.json'),'--report',str(root/'report.json'),'--review',str(root/'review.json'),'--asof',c['locked_at']])
            self.assertEqual(rc,0,result.getvalue());self.assertFalse(json.loads(result.getvalue())['wager_approved'])


if __name__=='__main__':unittest.main()
