"""Real-row software examples and reviewed SDG chains; no invented importance ratings."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.tests.test_future import clients, HEADERS
from backend.app.models import RoleTechnology, Skill, Profile, ProfileSkill, SDGLink, RoleSkill
from backend.app.software_skills import import_software, parse_software, SOFTWARE_URL
from backend.app.skill_extraction import extract, normalize, provider_schema
from backend.app.skill_catalogue import retrieve_candidates, MAX_MODEL_CANDIDATES


def seed(engine,tmp_path):
    raw=Path('data/fixtures/software_skills.csv').read_bytes()
    (tmp_path/'software_skills.csv').write_bytes(raw)
    (tmp_path/'manifest.json').write_text(json.dumps({'software_skills.csv':{'url':SOFTWARE_URL,'sha256':hashlib.sha256(raw).hexdigest(),
        'retrieved_at':'2026-10-21T14:36:52.644493+00:00','is_subset':True,'parent_sha256':'6aabb96b464288db849580e6510530efff3f80e25dde2bb23f1fc36bb526b016'}}))
    return import_software(engine,tmp_path)


def create(client,skill_ids,interests=None,custom=None):
    pid=client.post('/api/profiles',json={'is_demo':True},headers=HEADERS).json()['id']
    entries=[{'skill_id':sid,'level':'working'} for sid in skill_ids]
    draft={'current_field':'Illustrative computing study','skills':entries,'interests':interests or [],'custom_skills':custom or []}
    response=client.put(f'/api/profiles/{pid}/skills',json={'skills':entries,'interests':interests or [],'onboarding':draft},headers=HEADERS)
    assert response.status_code==200
    return pid


def test_import_deduplicates_preserves_flags_and_does_not_add_importance(clients,tmp_path):
    _,_,engine=clients
    result=seed(engine,tmp_path)
    assert result['software_skills']==8 and result['occupation_associations']==13
    assert seed(engine,tmp_path)==result
    with Session(engine) as db:
        ids=list(db.scalars(select(Skill.id).where(Skill.category=='software')))
        assert len(ids)==8 and not list(db.scalars(select(RoleSkill).where(RoleSkill.skill_id.in_(ids))))
        assert all(link.source_id==result['source_id'] for link in db.scalars(select(RoleTechnology)))
    raw=Path('data/fixtures/software_skills.csv').read_bytes().replace(b',Y,Y',b',X,Y',1)
    with pytest.raises(ValueError,match='flag'):parse_software(raw,{'15-1252.00'})


def test_search_exposes_total_categories_aliases_and_actual_role_relevance(clients,tmp_path):
    a,_,engine=clients;seed(engine,tmp_path)
    sql=a.get('/api/skill-catalogue?q=SQL&category=software&roles=15-2051.00').json()
    assert sql['catalogue_total']==43 and sql['counts']=={'core':35,'software':8}
    assert sql['skills'][0]['canonical_name']=='Structured query language SQL'
    assert sql['skills'][0]['relevant_to_targets'] and sql['skills'][0]['source_url']== 'https://www.onetcenter.org/dictionary/31.0/csv/software_skills.html'
    assert len(a.get('/api/skills?core=true').json()['skills'])==35
    sid=sql['skills'][0]['id']
    assert len(a.get('/api/skills',params={'core':'true','ids':sid}).json()['skills'])==36
    assert a.get('/api/skill-catalogue?limit=100').status_code==422


def test_extraction_keeps_python_sql_js_specific_without_automatic_broad_credit(clients,tmp_path):
    _,_,engine=clients;seed(engine,tmp_path)
    with Session(engine) as db:
        skills=list(db.scalars(select(Skill)))
        result=extract('I used Python, SQL and JS in an illustrative project.',skills,use_ai=False)
        names={s.id:s.canonical_name for s in skills}
        choices={names[sid] for candidate in result.candidates for sid in candidate.options}
        assert {'Python','Structured query language SQL','JavaScript'}<=choices
        assert 'Programming' not in choices
        assert names[normalize('JS',skills)[1][0]]=='JavaScript'


def test_provider_candidates_are_bounded_and_invalid_ids_cannot_escape(clients,tmp_path,monkeypatch):
    from backend.app import skill_extraction
    _,_,engine=clients;seed(engine,tmp_path)
    with Session(engine) as db:skills=list(db.scalars(select(Skill)))
    fake=[SimpleNamespace(id='tech:'+str(i),canonical_name='Tool'+str(i),aliases=[],category='software') for i in range(1000)]
    candidates=retrieve_candidates(' '.join(s.canonical_name for s in fake),skills+fake)
    assert len(candidates)==MAX_MODEL_CANDIDATES
    assert all(s in candidates for s in skills if s.category!='software')
    def provider(text,received):
        assert len(received)<=120
        return {'skills':[{'mention':'Python','years':None,'evidence_excerpt':'Python','confidence':'high','canonical_skill_ids':['invented']}]}
    monkeypatch.setattr(skill_extraction,'provider_extract',provider)
    assert extract('Python and SQL were used for a project.',skills,True).mode=='manual_fallback'


def test_specific_profiles_change_technical_connections_not_broad_readiness(clients,tmp_path):
    a,b,engine=clients;seed(engine,tmp_path)
    with Session(engine) as db:ids={s.canonical_name:s.id for s in db.scalars(select(Skill))}
    first=create(a,[ids[n] for n in ['Python','R','Structured query language SQL']],['15-2051.00'])
    create(b,[ids[n] for n in ['JavaScript','Cascading style sheets CSS','Hypertext markup language HTML']],['15-1252.00'])
    fa=a.get('/api/profiles/current/future').json();fb=b.get('/api/profiles/current/future').json()
    ma=next(m for m in fa['matches'] if m['role_id']=='15-2051.00')
    mb=next(m for m in fb['matches'] if m['role_id']=='15-1252.00')
    assert ma['technical']['matched_count']==3 and mb['technical']['matched_count']==3
    assert {s['name'] for s in ma['technical']['matched']}!={s['name'] for s in mb['technical']['matched']}
    assert ma['score']==mb['score']==0 and ma['readiness_status']==mb['readiness_status']=='not_assessed'
    graph=a.get('/api/profiles/current/career-graph').json()
    with Session(engine) as db:
        for edge in graph['edges']:
            if edge['type']=='uses_technology':
                row=db.get(RoleTechnology,(edge['source'].removeprefix('role:'),edge['target'].removeprefix('skill:')))
                assert row.source_id in edge['source_ids'] and edge['importance'] is None and edge['gap'] is None
        assert len(list(db.scalars(select(ProfileSkill).where(ProfileSkill.profile_id==first))))==3


def test_custom_skills_stay_private_unmapped_context_without_catalogue_insertion(clients):
    a,b,engine=clients
    custom=[{'name':name,'level':'working'} for name in ['Example custom skill A','Example custom skill B','Example custom skill C']]
    pid=create(a,[],['15-2051.00'],custom)
    future=a.get('/api/profiles/current/future').json()
    assert future['analysis_context']['custom_skills'][0]['name']=='Example custom skill A'
    target=next(m for m in future['matches'] if m['is_target'])
    assert target['score']==0 and target['readiness_status']=='not_assessed'
    assert b.get(f'/api/profiles/{pid}').status_code==404
    with Session(engine) as db:assert not list(db.scalars(select(Skill).where(Skill.canonical_name.like('Example custom%'))))


def test_adding_multiple_software_skills_never_double_counts_broad_readiness(clients,tmp_path):
    a,_,engine=clients;seed(engine,tmp_path)
    with Session(engine) as db:ids={s.canonical_name:s.id for s in db.scalars(select(Skill))}
    broad=[ids[name] for name in ['Programming','Writing','Critical Thinking']]
    pid=create(a,broad,['15-2051.00'])
    before=next(m for m in a.get('/api/profiles/current/future').json()['matches'] if m['role_id']=='15-2051.00')
    entries=[{'skill_id':sid,'level':'working'} for sid in broad+[ids[name] for name in ['Python','JavaScript','Structured query language SQL']]]
    draft={'current_field':'Illustrative computing study','skills':entries,'interests':['15-2051.00']}
    assert a.put(f'/api/profiles/{pid}/skills',json={'skills':entries,'interests':draft['interests'],'onboarding':draft},headers=HEADERS).status_code==200
    after=next(m for m in a.get('/api/profiles/current/future').json()['matches'] if m['role_id']=='15-2051.00')
    assert before['score']==after['score'] and after['technical']['matched_count']==3


def test_sdg_context_chain_is_reviewed_but_never_upgraded_to_direct_impact(clients):
    a,_,engine=clients
    create(a,['2.A.1.a','2.A.1.c','2.A.2.a'],['15-2051.00'])
    graph=a.get('/api/profiles/current/career-graph').json()
    assert graph['impact']['reviewed_links']>0
    context=[e for e in graph['edges'] if e['type']=='context_requirement' and e['source']=='role:15-2051.00']
    assert context
    with Session(engine) as db:
        for edge in context:
            row=db.get(RoleSkill,('15-2051.00',edge['target'].removeprefix('skill:')))
            assert edge['importance']==row.required_importance and 2<=edge['importance']<3 and edge['gap'] is None
        for edge in graph['edges']:
            if edge['type']=='contributes_to_target':
                row=db.get(SDGLink,edge['supporting_id'])
                assert row.curation_status=='human_reviewed' and row.reviewed_by and row.reviewed_at
                assert edge['source']==('role:'+row.role_id if row.role_id else 'skill:'+row.skill_id)
        for row in db.scalars(select(SDGLink)):row.curation_status='pending_review'
        db.commit()
    pending=a.get('/api/profiles/current/career-graph').json()
    assert pending['impact']['reviewed_links']==0 and pending['impact']['pending_links']>0
    assert not any(e['type']=='contributes_to_target' for e in pending['edges'])


def test_guide_retrieves_source_software_without_fabricating_importance(clients,tmp_path):
    from backend.app.agents.tools import invoke
    a,_,engine=clients;seed(engine,tmp_path)
    with Session(engine) as db:ids={s.canonical_name:s.id for s in db.scalars(select(Skill))}
    pid=create(a,[ids[n] for n in ['Python','R','Structured query language SQL']],['15-2051.00'])
    with Session(engine) as db:
        requirements=invoke('get_role_requirements',json.dumps({'role_id':'15-2051.00'}),db.get(Profile,pid),db,{'15-2051.00'})
        software=[row for row in requirements if row['evidence_kind']=='software_association']
        assert any(row['name']=='Python' for row in software)
        assert all(row['importance'] is None for row in software)
        assert all(db.get(RoleTechnology,('15-2051.00',row['skill_id'])).source_id==row['source_id'] for row in software)
