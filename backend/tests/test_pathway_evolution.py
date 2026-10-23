"""Exercise review gates, isolation and non-destructive revisions without providers."""
import copy
from sqlalchemy.orm import Session
from backend.tests.test_future import clients, HEADERS
from backend.tests.test_pathway_research import providers, prepare, start, latest
from backend.app import pathway_evolution as evolution
from backend.app.models import PathwayResearch


def saved(a):
    _, role = prepare(a)
    rid = start(a, role)
    a.post(f'/api/pathway-research/{rid}/review', json={'items':[{'requirement_id':'r1','starting_point':'practice'}]}, headers=HEADERS)
    a.post(f'/api/pathway-research/{rid}/accept', headers=HEADERS)
    return rid, role


def check(a, rid, mode='simulation'):
    return a.post(f'/api/pathway-research/{rid}/updates', json={'mode':mode}, headers=HEADERS)


def decide(a, rid, cid, action='accept'):
    return a.post(f'/api/pathway-research/{rid}/updates/decision', json={'check_id':cid,'action':action}, headers=HEADERS)


def test_simulation_review_isolated_and_deduplicated(clients, providers):
    a,b,engine=clients
    rid,role=saved(a)
    before=latest(a,role)['project']
    assert check(a,rid).status_code==200
    update=latest(a,role)['evolution']
    assert update['status']=='pending_review'
    assert check(a,rid).status_code==409
    assert decide(b,rid,update['id']).status_code in {401,404}
    assert a.post(f'/api/pathway-research/{rid}/updates',json={'mode':'simulation'}).status_code==403
    assert decide(a,rid,update['id']).status_code==200
    assert latest(a,role)['project']==before
    assert decide(a,rid,update['id']).status_code==409
    assert check(a,rid).json()['evolution']['status']=='no_change'
    with Session(engine) as db:
        payload=db.get(PathwayResearch,rid).payload
        assert 'project_versions' not in payload
        assert payload['update_history'][0]['reviewed_by']=='profile_owner'


def test_real_revision_preserves_work_and_rechecks_evidence(clients, providers, monkeypatch):
    a,_,engine=clients
    rid,role=saved(a)
    check(a,rid)
    draft=latest(a,role)['evolution']['draft']
    decide(a,rid,latest(a,role)['evolution']['id'],'dismiss')
    sources=[{'id':'simulation-1','statement':'Fixture public evidence','title':'Fixture','url':'https://example.com','market':'Global','period':'2026','scope':'equivalent'}]
    monkeypatch.setattr(evolution,'signals',lambda *args: sources)
    monkeypatch.setattr(evolution.research,'structured',lambda *args:evolution.UpdateDraft.model_validate(draft))
    before=copy.deepcopy(latest(a,role)['project'])
    mid=before['milestones'][0]['id']
    a.put(f'/api/pathway-research/{rid}/progress',json={'milestone_id':mid,'note':'Checked the result and recorded meaningful reviewer feedback.','status':'completed'},headers=HEADERS)
    before=latest(a,role)['project']
    check(a,rid,'evidence')
    cid=latest(a,role)['evolution']['id']
    original=copy.deepcopy(sources)
    sources.clear()
    assert decide(a,rid,cid).status_code==409
    sources.extend(original)
    assert decide(a,rid,cid).status_code==200
    after=latest(a,role)['project']
    assert after['milestones'][:-1]==before['milestones']
    assert len(after['milestones'])==len(before['milestones'])+1
    with Session(engine) as db:
        assert db.get(PathwayResearch,rid).payload['project_versions'][0]['project']==before


def test_no_evidence_and_invalid_citations_do_not_change_project(clients, providers, monkeypatch):
    a,_,_=clients
    rid,role=saved(a)
    monkeypatch.setattr(evolution,'signals',lambda *args: [])
    assert check(a,rid,'evidence').json()['evolution']['status']=='no_change'
    check(a,rid)
    draft=latest(a,role)['evolution']['draft']
    decide(a,rid,latest(a,role)['evolution']['id'],'dismiss')
    monkeypatch.setattr(evolution,'signals',lambda *args: [{'id':'different'}])
    monkeypatch.setattr(evolution.research,'structured',lambda *args:evolution.UpdateDraft.model_validate(draft))
    before=latest(a,role)['project']
    check(a,rid,'evidence')
    assert latest(a,role)['evolution']['status']=='failed'
    assert latest(a,role)['project']==before


def test_source_selection_excludes_pending_stale_and_demand_only(monkeypatch):
    from types import SimpleNamespace
    base={'id':'approved','current':True,'dimension':'change','statement':'A reviewed capability change.',
          'source':{'url':'https://example.com','title':'Fixture source'},'market':'Global',
          'observation_period':'2026','mapping':{'relationship':'source_broader'},'valid_until':'2099-01-01'}
    monkeypatch.setattr(evolution,'load_evidence',lambda db:{})
    monkeypatch.setattr(evolution,'role_outlook',lambda *args:{'evidence':[base,base,
        {**base,'id':'pending','current':False},{**base,'id':'expired','current':False},
        {**base,'id':'demand','dimension':'demand'}]})
    sources=evolution.signals(None,SimpleNamespace(role_id='role',payload={'market':'Malaysia'}))
    assert [s['id'] for s in sources]==['approved']
    assert sources[0]['scope']=='source_broader'


def test_no_change_is_reused_and_expired_check_is_reported(clients, providers, monkeypatch):
    from datetime import timedelta
    a,_,engine=clients
    rid,role=saved(a)
    monkeypatch.setattr(evolution,'signals',lambda *args:[{'id':'reviewed'}])
    calls=[]
    def no_change(*args):
        calls.append(True)
        return evolution.UpdateDraft(reason='Existing milestones already cover this change.',implications=[],addition=None)
    monkeypatch.setattr(evolution.research,'structured',no_change)
    check(a,rid,'evidence')
    assert latest(a,role)['evolution']['status']=='no_change'
    check(a,rid,'evidence')
    assert len(calls)==1
    with Session(engine) as db:
        run=db.get(PathwayResearch,rid)
        value=copy.deepcopy(run.payload['evolution'])
        value.update(status='analyzing',deadline=(evolution.research.now()-timedelta(seconds=1)).isoformat())
        evolution.save(run,value)
        db.commit()
    assert latest(a,role)['evolution']['status']=='failed'
