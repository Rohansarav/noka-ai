"""Job-to-project flow: grounding, isolation, explicit review and durable evidence."""
from datetime import timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.tests.test_future import clients, profile, HEADERS
from backend.app import pathway_research as service
from backend.app.config import Settings
from backend.app.models import PathwayResearch
from backend.app.pathway_contracts import Extraction, ProjectDraft

DESCRIPTION = 'Software Developer in Malaysia. Responsibilities include designing reliable Python services. Required: write automated tests and document architecture decisions. This is a fixture job description.'
QUOTE = 'write automated tests and document architecture decisions'


def extraction(quote=QUOTE):
    return Extraction(postings=[{'source_id':'s1','is_job':True,'relevant':True,'location':'Malaysia','availability':'not_verified','reason':'Fixture role and location match.'}],
        requirements=[{'source_id':'s1','title':'Test and document services','quote':quote,'priority':'required'}])


def project():
    return ProjectDraft(title='Reliable service for a campus team', problem='Validate whether a campus team needs a reliable request tracking service.',
        audience='A campus support team', why_you='Use your existing programming experience and validate unassessed testing ability.',
        scope='One small service, a documented design and repeatable tests.', assumptions=['Access to a willing reviewer must be confirmed.'],
        milestones=[{'title':title,'objective':'Validate and demonstrate one concrete part of the service.',
            'requirement_ids':['r1'],'steps':['Define the intended outcome.','Build and check the work sample.'],
            'deliverable':'A reviewed work sample with documented limitations.',
            'acceptance_criteria':['Record feedback from a reviewer.','Include a repeatable check.'],
            'learn':'Study test design and architecture trade-offs as needed.','effort_hours':4}
            for title in ['Validate the problem','Build the service','Evaluate the result']])


def prepare(client):
    pid=profile(client,{'2.A.2.a':'strong','2.B.3.e':'working','2.A.1.e':'working'})
    role=client.get('/api/profiles/current/future').json()['matches'][0]['role_id']
    assert client.put('/api/profiles/current/future',json={'role_id':role},headers=HEADERS).status_code==200
    return pid,role


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(service,'get_settings',lambda:Settings(openai_api_key='fixture',tavily_api_key='fixture'))
    monkeypatch.setattr(service,'structured',lambda schema,*args:extraction() if schema is Extraction else project())


def start(client,role,**extra):
    response=client.post('/api/pathway-research',json={'role_id':role,'description':DESCRIPTION,**extra},headers=HEADERS)
    assert response.status_code==202,response.text
    return response.json()['id']


def latest(client,role):
    response=client.get('/api/pathway-research',params={'role_id':role})
    assert response.status_code==200,response.text
    return response.json()['runs'][0]


def test_review_project_progress_refresh_and_ownership(clients,providers):
    a,b,engine=clients
    pid,role=prepare(a)
    prepare(b)
    rid=start(a,role)
    found=latest(a,role)
    assert found['status']=='review' and found['review'] is None and found['project'] is None
    assert found['requirements'][0]['quote']==QUOTE
    assert latest(a,role)['sources'][0]['origin']=='manual'
    review={'items':[{'requirement_id':'r1','starting_point':'practice'}]}
    assert b.post(f'/api/pathway-research/{rid}/review',json=review,headers=HEADERS).status_code==404
    assert a.post(f'/api/pathway-research/{rid}/review',json=review).status_code==403
    assert a.post(f'/api/pathway-research/{rid}/review',json={'items':[{'requirement_id':'fake','starting_point':'learn'}]},headers=HEADERS).status_code==422
    assert a.post(f'/api/pathway-research/{rid}/review',json=review,headers=HEADERS).status_code==202
    planned=latest(a,role)
    assert planned['status']=='ready' and planned['review']['reviewed_by']=='profile_owner'
    assert planned['project']['accepted_at'] is None
    mid=planned['project']['milestones'][0]['id']
    progress={'milestone_id':mid,'note':'Checked the design with a reviewer and documented limitations.','status':'completed'}
    assert a.put(f'/api/pathway-research/{rid}/progress',json=progress,headers=HEADERS).status_code==409
    assert a.post(f'/api/pathway-research/{rid}/accept',headers=HEADERS).status_code==200
    assert a.put(f'/api/pathway-research/{rid}/progress',json={**progress,'note':'short'},headers=HEADERS).status_code==422
    assert a.put(f'/api/pathway-research/{rid}/progress',json=progress,headers=HEADERS).status_code==200
    start(a,role)
    runs=a.get('/api/pathway-research',params={'role_id':role}).json()['runs']
    old=next(r for r in runs if r['id']==rid)
    assert old['project']['milestones'][0]['note']==progress['note']
    assert old['project']['milestones'][0]['status']=='completed'
    assert b.get('/api/pathway-research',params={'role_id':role}).json()['runs']==[]
    assert a.delete(f'/api/profiles/{pid}',headers=HEADERS).status_code==204
    with Session(engine) as db: assert not list(db.scalars(select(PathwayResearch)))


def test_invalid_quote_and_missing_credentials_are_honest(clients,providers,monkeypatch):
    a,_,_=clients
    _,role=prepare(a)
    monkeypatch.setattr(service,'structured',lambda *args:extraction('An invented requirement not in the source'))
    start(a,role)
    assert latest(a,role)['status']=='failed'
    assert latest(a,role)['requirements']==[]
    monkeypatch.setattr(service,'get_settings',lambda:Settings(openai_api_key=None,tavily_api_key=None))
    start(a,role)
    assert 'not configured' in latest(a,role)['error']


def test_web_research_is_bounded_and_never_receives_profile_text(clients,providers,monkeypatch):
    a,_,_=clients
    _,role=prepare(a)
    requests=[]
    class Response:
        def __init__(self,data):self.data=data
        def raise_for_status(self):pass
        def json(self):return self.data
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json,**kwargs):
            requests.append((url,json))
            if url.endswith('/search'):
                return Response({'results':[{'url':'https://careers.example.com/jobs/one','title':'Fixture developer job'},{'url':'https://linkedin.com/jobs/private','title':'Restricted'}]})
            return Response({'results':[{'url':'https://careers.example.com/jobs/one','raw_content':DESCRIPTION}]})
    monkeypatch.setattr(service.httpx,'Client',Client)
    start(a,role,description='')
    run=latest(a,role)
    assert run['status']=='review'
    assert len(requests)==3
    assert requests[-1][1]['urls']==['https://careers.example.com/jobs/one']
    assert all(set(body)<= {'query','max_results','search_depth','exclude_domains','include_raw_content','urls','extract_depth','timeout'} for _,body in requests)
    assert any(e['stage']=='extracting' for e in run['events'])
    assert run['sources'][0]['availability']=='not_verified'


def test_recovery_and_failed_generation_preserve_review(clients,providers,monkeypatch):
    a,_,engine=clients
    _,role=prepare(a)
    rid=start(a,role)
    def fail(*args):raise ValueError('provider fixture failure')
    monkeypatch.setattr(service,'structured',fail)
    review={'items':[{'requirement_id':'r1','starting_point':'unassessed'}]}
    a.post(f'/api/pathway-research/{rid}/review',json=review,headers=HEADERS)
    assert latest(a,role)['status']=='failed' and latest(a,role)['review']
    with Session(engine) as db:
        run=db.get(PathwayResearch,rid);run.status='planning';run.deadline=service.now()-timedelta(seconds=1);db.commit()
    assert 'restarted' in latest(a,role)['error']
    assert not service.advance(engine,rid,'ready','Late worker result',project=project().model_dump())


@pytest.mark.parametrize('url',['http://example.com','https://127.0.0.1/a','https://user:pass@example.com','https://linkedin.com/jobs/1','https://example.com/?token=secret','file:///private','https://host.internal/a'])
def test_source_url_safety(url):
    assert service.public_url(url) is None


def test_closed_jobs_and_invented_project_links_are_rejected(clients,providers,monkeypatch):
    parsed=extraction();parsed.postings[0].availability='explicitly_closed'
    assert service.grounded(parsed,[{'id':'s1'}],{'s1':DESCRIPTION})==([],[])
    a,_,_=clients
    _,role=prepare(a);rid=start(a,role)
    def invalid(*args):
        p=project();p.milestones[0].requirement_ids=['invented'];return p
    monkeypatch.setattr(service,'structured',invalid)
    a.post(f'/api/pathway-research/{rid}/review',json={'items':[{'requirement_id':'r1','starting_point':'learn'}]},headers=HEADERS)
    assert latest(a,role)['status']=='failed' and latest(a,role)['project'] is None


def test_saved_projects_survive_history_window_and_active_run_blocks_duplicates(clients,providers):
    a,_,engine=clients
    _,role=prepare(a);rid=start(a,role)
    a.post(f'/api/pathway-research/{rid}/review',json={'items':[{'requirement_id':'r1','starting_point':'learn'}]},headers=HEADERS)
    with Session(engine) as db:
        original=db.get(PathwayResearch,rid)
        original.created_at=service.now()-timedelta(days=30)
        for i in range(22):
            db.add(PathwayResearch(id=f'history-fixture-{i}',profile_id=original.profile_id,role_id=role,
                created_at=service.now()-timedelta(days=2,minutes=i),updated_at=service.now(),deadline=service.now(),status='failed',
                payload={'target':'Fixture','market':'Malaysia','events':[]}))
        db.commit()
    runs=a.get('/api/pathway-research',params={'role_id':role}).json()['runs']
    assert len(runs)==21 and any(r['id']==rid and r['project'] for r in runs)
    with Session(engine) as db:
        run=db.get(PathwayResearch,rid);run.status='planning';run.created_at=service.now();run.deadline=service.now()+timedelta(seconds=30);db.commit()
    assert a.post('/api/pathway-research',json={'role_id':role},headers=HEADERS).status_code==429


def test_provider_timeout_is_specific_and_body_is_bounded(clients,providers,monkeypatch):
    a,_,_=clients
    _,role=prepare(a)
    def timeout(*args):raise service.httpx.ReadTimeout('Do not expose this provider text')
    monkeypatch.setattr(service,'structured',timeout)
    start(a,role)
    result=latest(a,role)
    assert result['status']=='failed' and 'timed out' in result['error']
    assert 'Do not expose' not in str(result)
    assert a.post('/api/pathway-research',json={'role_id':role,'description':'x'*100001},headers=HEADERS).status_code==413
