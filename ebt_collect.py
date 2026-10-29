"""Bounded public-source collection and capture-bound extraction; no evasions."""
import hashlib,json,re,urllib.request,urllib.error,urllib.robotparser,uuid
from datetime import date,datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urljoin
from ebt_json import strict_json
from ebt_validation import clock,number

AGENT='EBT-Sports-Research/0.1'
NBA_URL='https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json'

def source_kind(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.fragment:raise ValueError('unsupported source URL')
    if url==NBA_URL:return 'nba_scoreboard'
    if p.hostname=='www.teamrankings.com' and re.fullmatch(r'/nba/stat/[a-z0-9-]+',p.path):
        q=parse_qs(p.query,keep_blank_values=True)
        if set(q)=={'date'} and len(q['date'])==1:
            date.fromisoformat(q['date'][0]);return 'teamrankings_table'
    raise ValueError('URL is not a supported source endpoint')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('redirect requires canonical-URL review')

def _get(url,timeout,max_bytes):
    request=urllib.request.Request(url,headers={'User-Agent':AGENT,'Accept':'application/json,text/html,text/plain'})
    with urllib.request.build_opener(NoRedirect).open(request,timeout=timeout) as response:
        if response.status!=200:raise ValueError('unexpected HTTP status')
        body=response.read(max_bytes+1)
        if len(body)>max_bytes:raise ValueError('response exceeds byte limit')
        return body,response.headers.get_content_type()

def collect(url,destination,*,timeout=10,max_bytes=4000000,_fetch=None):
    kind=source_kind(url)
    if type(timeout) is not int or not 1<=timeout<=30 or type(max_bytes) is not int or not 1<=max_bytes<=10000000:raise ValueError('invalid collection bounds')
    fetch=_fetch or _get
    try:
        p=urlsplit(url);robots_url=p.scheme+'://'+p.netloc+'/robots.txt'
        try:
            robots,_=fetch(robots_url,timeout,min(max_bytes,1000000))
            rules=urllib.robotparser.RobotFileParser();rules.parse(robots.decode('utf-8',errors='strict').splitlines())
            if not rules.can_fetch(AGENT,url):return {'status':'HOLD','reason':'robots disallows collection','url':url}
            if rules.crawl_delay(AGENT) is not None or rules.request_rate(AGENT) is not None:return {'status':'HOLD','reason':'robots rate directive requires a reviewed scheduler','url':url}
        except urllib.error.HTTPError as error:
            if error.code!=404:raise
        body,content_type=fetch(url,timeout,max_bytes)
        if not body:raise ValueError('empty source response')
        allowed={'application/json'} if kind=='nba_scoreboard' else {'text/html','application/xhtml+xml'}
        if content_type not in allowed:raise ValueError('unexpected source content type')
        retrieved=datetime.now(timezone.utc).isoformat();digest=hashlib.sha256(body).hexdigest()
        root=Path(destination);root.mkdir(parents=True,exist_ok=True);path=root/(digest+'.bin')
        try:
            with path.open('xb') as handle:handle.write(body)
        except FileExistsError:
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('existing capture mismatch')
        receipt={'schema_version':'1.0','status':'COLLECTED','adapter':kind,'url':url,'retrieved_at':retrieved,'raw_path':path.name,'raw_sha256':digest,'bytes':len(body),'content_type':content_type,'robots_checked':True,'source_truth_verified':False}
        receipt_path=root/('receipt-'+uuid.uuid4().hex+'.json')
        with receipt_path.open('x') as handle:json.dump(receipt,handle,indent=2)
        return {**receipt,'receipt_path':str(receipt_path)}
    except (OSError,ValueError,UnicodeError) as error:
        return {'status':'HOLD','reason':str(error),'url':url,'adapter':kind}

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.tables=[];self.table=None;self.row=None;self.cell=None;self.link=None;self.h1=[];self.in_h1=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='h1':self.in_h1=True
        if tag=='table':
            if self.table is not None:raise ValueError('nested tables require adapter review')
            self.table=[]
        elif self.table is not None and tag=='tr':self.row=[]
        elif self.row is not None and tag in ('td','th'):self.cell=[];self.link=None
        elif self.cell is not None and tag=='a':self.link=a.get('href')
    def handle_data(self,text):
        if self.in_h1:self.h1.append(text)
        if self.cell is not None:self.cell.append(text)
    def handle_endtag(self,tag):
        if tag=='h1':self.in_h1=False
        if tag in ('td','th') and self.cell is not None:
            self.row.append((' '.join(''.join(self.cell).split()),self.link));self.cell=None
        elif tag=='tr' and self.row is not None:
            self.table.append(self.row);self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table);self.table=None

def tr_table(body,*,expected_heading,column,expected_rows):
    if not isinstance(expected_heading,str) or not expected_heading or not isinstance(column,str) or not column or type(expected_rows) is not int or expected_rows<=0:raise ValueError('explicit heading, column and expected row count required')
    parser=Tables();parser.feed(body.decode('utf-8'))
    if ' '.join(''.join(parser.h1).split())!=expected_heading:raise ValueError('page heading mismatch')
    candidates=[t for t in parser.tables if t and [c[0] for c in t[0]][:2]==['Rank','Team'] and column in [c[0] for c in t[0]]]
    if len(candidates)!=1:raise ValueError('ambiguous or missing statistical table')
    table=candidates[0];headers=[c[0] for c in table[0]]
    if len(headers)!=len(set(headers)):raise ValueError('duplicate table headers')
    index=headers.index(column);rows=[];names=set();ranks=set()
    for row_number,row in enumerate(table[1:],1):
        if len(row)!=len(headers):raise ValueError('table row width mismatch')
        rank=int(row[0][0]);name=row[1][0];team_link=row[1][1]
        if not name or name in names or rank in ranks or not 1<=rank<=expected_rows or not team_link:raise ValueError('invalid/duplicate team identity or rank')
        team_url=urljoin('https://www.teamrankings.com',team_link)
        if urlsplit(team_url).hostname!='www.teamrankings.com' or not urlsplit(team_url).path.startswith('/nba/team/'):raise ValueError('unexpected team link')
        text=row[index][0];value=number(text.replace(',','').removesuffix('%'))
        rows.append({'source_row':row_number,'rank':rank,'source_team_name':name,'source_team_url':team_url,'column':column,'source_text':text,'value':str(value),'display_unit':'percent_points' if text.endswith('%') else 'numeric'})
        names.add(name);ranks.add(rank)
    if len(rows)!=expected_rows:raise ValueError('unexpected statistical row count')
    return {'heading':expected_heading,'column':column,'rows':rows,'canonical_team_mapping_verified':False}

def nba_scoreboard(body,*,expected_date):
    date.fromisoformat(expected_date);data=strict_json(body.decode('utf-8'));board=data['scoreboard']
    if board['gameDate']!=expected_date or board['leagueId']!='00':raise ValueError('NBA league/date mismatch')
    if not isinstance(board['games'],list):raise ValueError('game list required')
    games=[];seen=set()
    for game in board['games']:
        identity=game['gameId'];home=game['homeTeam']['teamId'];away=game['awayTeam']['teamId']
        if not isinstance(identity,str) or not re.fullmatch(r'\d{10}',identity) or identity in seen:raise ValueError('invalid or duplicate game ID')
        if type(home) is not int or type(away) is not int or min(home,away)<=0 or home==away:raise ValueError('invalid team IDs')
        if type(game['gameStatus']) is not int or game['gameStatus'] not in (1,2,3):raise ValueError('unrecognized NBA game status')
        games.append({'event_id':identity,'home_team_id':str(home),'away_team_id':str(away),'start_utc':clock(game['gameTimeUTC']).isoformat(),'status_code':game['gameStatus']});seen.add(identity)
    return {'league_date':expected_date,'games':games,'feed_rows':len(games),'independent_schedule_corroboration':False}

def extract(receipt,raw_root,*,parameters):
    if not isinstance(receipt,dict):raise ValueError('capture receipt object required')
    if receipt.get('status')!='COLLECTED' or receipt.get('schema_version')!='1.0':raise ValueError('successful capture receipt required')
    adapter=source_kind(receipt['url'])
    if adapter!=receipt['adapter']:raise ValueError('source/adapter mismatch')
    root=Path(raw_root).resolve(strict=True);relative=Path(receipt['raw_path'])
    if relative.is_absolute():raise ValueError('relative capture path required')
    path=(root/relative).resolve(strict=True)
    if not path.is_relative_to(root):raise ValueError('capture escape')
    body=path.read_bytes()
    if hashlib.sha256(body).hexdigest()!=receipt['raw_sha256'] or len(body)!=receipt['bytes']:raise ValueError('capture integrity mismatch')
    value=tr_table(body,**parameters) if adapter=='teamrankings_table' else nba_scoreboard(body,**parameters)
    return {'adapter':adapter,'adapter_version':'1.0','raw_sha256':receipt['raw_sha256'],'parameters':parameters,'extracted':value,'extraction_reproducible':True,'source_truth_verified':False,'forecast_approved':False}

def verify_extraction(receipt,raw_root,claim,expected_parameters=None):
    if not isinstance(claim,dict):raise ValueError('extraction claim object required')
    if expected_parameters is not None and claim.get('parameters')!=expected_parameters:return False
    return extract(receipt,raw_root,parameters=claim['parameters'])==claim
