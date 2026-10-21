"""Representative profile and source/contract checks for expanded career exploration."""
from pathlib import Path
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.tests.test_future import clients, profile, HEADERS
from backend.app.models import Profile, Role, RoleSkill
from backend.app.matching import match_profile, prioritize_gaps
from backend.app.future import ranked, SCENARIOS
from backend.app.ingestion.parsers import parse_onet

LEVELS={'2.A.2.a':'strong','2.B.3.e':'working','2.A.1.e':'working'}


def test_discovery_search_pagination_family_and_bounds(clients):
    a,_,_=clients
    first=a.get('/api/careers?limit=4').json()
    second=a.get('/api/careers?limit=4&offset=4').json()
    assert first['total']==25 and len(first['roles'])==4
    assert not {r['id'] for r in first['roles']} & {r['id'] for r in second['roles']}
    hints=a.get('/api/careers?q=Machine%20Learning%20Engineer').json()
    assert any(r['title']=='Data Scientists' and 'confirm' in r['match_reason'] for r in hints['roles'])
    assert all(r['family']=='15' for r in a.get('/api/careers?family=15').json()['roles'])
    assert a.get('/api/careers?limit=1000').status_code==422
    assert a.get('/api/careers?q='+('x'*121)).status_code==422
    assert not a.get('/api/careers?q=%25_unmatched').json()['roles']


def test_low_readiness_target_retained_without_bonus(clients):
    a,_,engine=clients
    pid=profile(a,LEVELS)
    with Session(engine) as db:
        all_before=match_profile(db.get(Profile,pid),db,limit=None)['matches']
    target=all_before[-1]['role_id']
    skills=[{'skill_id':sid,'level':level} for sid,level in LEVELS.items()]
    assert a.put(f'/api/profiles/{pid}/skills',json={'skills':skills,'interests':[target]},headers=HEADERS).status_code==200
    result=a.get(f'/api/profiles/{pid}/matches').json()['matches']
    chosen=next(m for m in result if m['role_id']==target)
    assert chosen['is_target'] and chosen['score']==all_before[-1]['score'] and chosen['interest_adjustment']==0
    assert len(result)==6
    for scenario in SCENARIOS:
        changed=a.put('/api/profiles/current/future',json={'scenario':scenario,'role_id':target},headers=HEADERS)
        assert changed.status_code==200
        assert next(m for m in changed.json()['matches'] if m['role_id']==target)['is_target']
        graph=a.get('/api/profiles/current/career-graph').json()
        assert any(n['entity_id']==target and n['is_target'] for n in graph['nodes'])


def test_custom_aspirations_validate_and_confirm_before_becoming_targets(clients):
    a,other,engine=clients
    pid=profile(a,LEVELS)
    skills=[{'skill_id':sid,'level':level} for sid,level in LEVELS.items()]
    draft={'current_field':'Computing','skills':skills,'aspirations':[{'title':'Machine Learning Engineer','status':'unmapped','role_ids':[]}]}
    body={'skills':skills,'onboarding':draft}
    assert a.put(f'/api/profiles/{pid}/skills',json=body,headers=HEADERS).status_code==200
    assert not a.get(f'/api/profiles/{pid}').json()['interests']
    draft['aspirations'][0].update(status='confirmed',role_ids=['15-2051.00'])
    assert a.put(f'/api/profiles/{pid}/skills',json=body,headers=HEADERS).status_code==200
    assert a.get(f'/api/profiles/{pid}').json()['interests']==['15-2051.00']
    with Session(engine) as db:
        assert db.get(Profile,pid).analysis_context['aspirations'][0]['title']=='Machine Learning Engineer'
    draft['aspirations'][0]['role_ids']=['invented']
    assert a.put(f'/api/profiles/{pid}/skills',json=body,headers=HEADERS).status_code==422
    assert other.put(f'/api/profiles/{pid}/skills',json=body,headers=HEADERS).status_code==404
    draft['aspirations'][0].update(status='unmapped',role_ids=['15-2051.00'])
    assert a.put(f'/api/profiles/{pid}/skills',json=body,headers=HEADERS).status_code==422


def test_saved_context_affects_relevance_not_readiness_and_drafts_are_isolated(clients):
    a,_,engine=clients
    pid=profile(a,LEVELS)
    skills=[{'skill_id':sid,'level':level} for sid,level in LEVELS.items()]
    def all_matches():
        with Session(engine) as db:return {m['role_id']:m for m in match_profile(db.get(Profile,pid),db,limit=None)['matches']}
    before=all_matches()
    draft={'current_field':'Computing','goal':'Analyse data and develop software','projects':'Software development and data analysis','constraints':'Evening learning','skills':skills}
    assert a.put(f'/api/profiles/{pid}/onboarding',json=draft,headers=HEADERS).status_code==200
    assert all_matches()==before
    assert a.put(f'/api/profiles/{pid}/skills',json={'skills':skills,'onboarding':draft},headers=HEADERS).status_code==200
    after=all_matches()
    assert all(after[r]['score']==before[r]['score'] for r in before)
    assert any(m['context_alignment']>0 and m['context_reasons'] for m in after.values())
    assert a.get('/api/profiles/current/future').json()['analysis_context']['constraints']=='Evening learning'


def test_graph_and_pathway_use_same_weighted_gap_order_for_each_world(clients):
    a,_,_=clients
    profile(a,LEVELS)
    future=a.get('/api/profiles/current/future').json()
    role=future['matches'][0]['role_id']
    for scenario in SCENARIOS:
        value=a.put('/api/profiles/current/future',json={'role_id':role,'scenario':scenario},headers=HEADERS).json()
        graph=a.get('/api/profiles/current/career-graph').json()
        graph_gaps={e['target'].removeprefix('skill:') for e in graph['edges'] if e['type']=='missing_skill' and e['source']=='role:'+role}
        assert graph_gaps=={task['skill_id'] for task in value['pathway'][:3]}
        priority=[task['planning_priority'] for task in value['pathway']]
        assert all(task['planning_priority']==round(task['priority']*(1.25 if task['scenario_priority'] else 1),4) for task in value['pathway'])
        assert priority==sorted(priority,reverse=True)
    gaps=[{'skill_id':'owned','name':'Writing','importance':4.5,'gap':.35,'priority':1.575}, {'skill_id':'absent','name':'Programming','importance':4,'gap':1,'priority':4}]
    assert prioritize_gaps(gaps,['Writing'])[0]['skill_id']=='absent'


def test_scenarios_rank_complete_catalogue_and_retain_explored_role(clients):
    a,_,engine=clients
    pid=profile(a,LEVELS)
    with Session(engine) as db:
        p=db.get(Profile,pid)
        base=match_profile(p,db,limit=None)['matches']
        original={m['role_id'] for m in base[:5]}
        assert any(set(m['role_id'] for m in ranked(p,db,s))-original for s in SCENARIOS)
    explored=base[-1]['role_id']
    for scenario in SCENARIOS:
        response=a.put('/api/profiles/current/future',json={'role_id':explored,'scenario':scenario},headers=HEADERS)
        assert response.status_code==200 and any(m['role_id']==explored for m in response.json()['matches'])


def test_import_includes_unselected_source_occupation_without_fake_sector():
    root=Path('data/fixtures')
    curated=json.loads(Path('data/curation/catalogue.json').read_text())['roles']
    occupations=(root/'occupation_data.csv').read_bytes()
    roles,_,links=parse_onet(occupations,{'essential':(root/'essential_skills.csv').read_bytes(),'transferable':(root/'transferable_skills.csv').read_bytes()},curated[:2],{r['sector'] for r in curated if r['sector']})
    assert len(roles)>2
    expanded=next(r for r in roles if r['id'] not in {c['occupation_code'] for c in curated[:2]})
    assert expanded['sector'] is None and expanded['curation_status']=='source_imported'
    assert any(link['role_id']==expanded['id'] for link in links)


def test_career_cache_checksum_failure_does_not_write(clients,tmp_path):
    import pytest
    from scripts.import_careers import import_careers
    _,_,engine=clients
    root=Path('data/fixtures')
    for name in ['manifest.json','occupation_data.csv','essential_skills.csv','transferable_skills.csv']:
        (tmp_path/name).write_bytes((root/name).read_bytes())
    with (tmp_path/'occupation_data.csv').open('ab') as output:
        output.write(b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        import_careers(engine,tmp_path)
    with Session(engine) as db:
        assert len(list(db.scalars(select(Role))))==25


def test_public_evidence_cache_is_immutable_and_explicitly_invalidated(clients):
    import pytest
    from dataclasses import FrozenInstanceError
    from sqlalchemy import event
    from backend.app.occupation_catalogue import occupation_evidence, invalidate_catalogue
    _,_,engine=clients
    calls=[]
    def record(*args):calls.append(1)
    event.listen(engine,'before_cursor_execute',record)
    try:
        with Session(engine) as db:
            first=occupation_evidence(db)
            count=len(calls)
            second=occupation_evidence(db)
            assert first is not second and first[0] is second[0] and len(calls)==count
            with pytest.raises(FrozenInstanceError):first[0][0].title='Not allowed'
            invalidate_catalogue(engine)
            third=occupation_evidence(db)
            assert len(calls)>count and third[0] is not first[0]
            assert all(not hasattr(r,'profile_id') for r in third[0])
    finally:
        event.remove(engine,'before_cursor_execute',record)
