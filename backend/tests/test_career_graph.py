"""Graph evidence and ownership checks use attributed fixture records, never market inventions."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.evidence_api import get_session
from backend.app.models import Base, Profile, RoleSkill, SDGLink, Skill
from backend.app.ingestion.runner import import_all
from backend.app.matching import LEVELS, match_profile
from backend.app.future import ranked, SCENARIOS
from backend.app.matching import prioritize_gaps
from backend.app.career_graph import MAX_GAPS_PER_ROLE, MAX_ROLES, MAX_SDG_LINKS
from backend.app.career_graph_schemas import MAX_EDGES, MAX_NODES

HEADERS = {"X-Noka-CSRF": "1", "Origin": "http://testserver"}
URL = '/api/profiles/current/career-graph'


@pytest.fixture
def graph_env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, record): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    import_all(engine, Path(__file__).resolve().parents[2] / 'data/fixtures', offline=True)
    def session():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_session] = session
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


def confirmed(client, engine, names=None, level='working'):
    pid = client.post('/api/profiles', json={'is_demo': True}, headers=HEADERS).json()['id']
    with Session(engine) as db:
        rows = list(db.scalars(select(Skill).where(Skill.canonical_name.in_(names or ['Science','Instructing','Programming','Critical Thinking','Writing','Active Learning']))))
    skills = [{'skill_id':s.id,'level':level,'years':None} for s in rows]
    result = client.put(f'/api/profiles/{pid}/skills', json={'skills':skills,'country':'MY','interests':[]},headers=HEADERS)
    assert result.status_code == 200
    return pid, skills


def test_missing_profile_is_honest_and_does_not_create_session(graph_env):
    client, engine = graph_env
    result = client.get(URL)
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    graph = result.json()
    assert graph['status'] == 'no_profile' and graph['profile_revision'] is None
    assert graph['nodes'] == graph['edges'] == graph['sources'] == []
    assert 'noka_session' not in client.cookies


def test_session_ownership_is_derived_not_selected_by_query(graph_env):
    client, engine = graph_env
    pid, _ = confirmed(client, engine)
    assert any(n['id'] == 'profile:'+pid for n in client.get(URL).json()['nodes'])
    with TestClient(app) as stranger:
        graph = stranger.get(URL + '?profile_id=' + pid).json()
        assert graph['status'] == 'no_profile' and not graph['nodes']
        other, _ = confirmed(stranger, engine, ['Writing'])
        graph = stranger.get(URL + '?profile_id=' + pid).json()
        assert {n['entity_id'] for n in graph['nodes'] if n['type']=='profile'} == {other}
        assert pid not in str(graph)


def test_insufficient_profile_keeps_real_skills_without_roles(graph_env):
    client, engine = graph_env
    pid, skills = confirmed(client, engine, ['Writing','Programming'])
    graph = client.get(URL).json()
    assert graph['status'] == 'insufficient_profile_information'
    assert len([n for n in graph['nodes'] if n['type']=='owned_skill']) == 2
    assert not any(n['type']=='role' for n in graph['nodes'])
    assert len([e for e in graph['edges'] if e['type']=='has_skill']) == 2


def test_typed_ids_endpoints_and_stable_ordering(graph_env):
    client, engine = graph_env
    confirmed(client, engine)
    first, second = client.get(URL).json(), client.get(URL).json()
    assert first['nodes'] == second['nodes'] and first['edges'] == second['edges']
    assert first['profile_revision'] == second['profile_revision']
    ids = [n['id'] for n in first['nodes']]
    assert len(ids) == len(set(ids)) and ids == sorted(ids)
    assert all(n['id'].startswith(('skill:' if n['type'] in ('owned_skill','required_skill') else n['type']+':')) for n in first['nodes'])
    assert all(e['source'] in ids and e['target'] in ids for e in first['edges'])
    assert [e['id'] for e in first['edges']] == sorted(e['id'] for e in first['edges'])


def test_graph_scores_are_exactly_the_existing_matcher(graph_env):
    client, engine = graph_env
    pid, skills = confirmed(client, engine)
    graph = client.get(URL).json()
    with Session(engine) as db:
        matching = match_profile(db.get(Profile,pid),db,limit=None)
        directions = ranked(db.get(Profile,pid),db,'collaboration')
    expected = {m['role_id']:m for m in directions}
    assert all(m['score']==next(base['score'] for base in matching['matches'] if base['role_id']==m['role_id']) for m in directions)
    actual = {n['entity_id']:n for n in graph['nodes'] if n['type']=='role'}
    assert set(actual) == set(expected)
    for rid in actual:
        assert actual[rid]['score'] == expected[rid]['score']
        assert actual[rid]['coverage'] == expected[rid]['coverage']
        assert actual[rid]['explanation'] == expected[rid]['explanation']
    assert graph['methodology'] == matching['methodology']


def test_role_edges_and_priority_gaps_have_real_attribution(graph_env):
    client, engine = graph_env
    pid, skills = confirmed(client, engine)
    graph = client.get(URL).json()
    levels = {s['skill_id']:LEVELS[s['level']] for s in skills}
    with Session(engine) as db:
        directions = ranked(db.get(Profile,pid),db,'collaboration')
        gaps = {m['role_id']:{g['skill_id']:g for g in prioritize_gaps(m['gaps'],SCENARIOS['collaboration']['skills'])[:MAX_GAPS_PER_ROLE]} for m in directions}
        for edge in graph['edges']:
            if edge['type'] not in ('requires_skill','missing_skill'): continue
            rid, sid = edge['source'].removeprefix('role:'), edge['target'].removeprefix('skill:')
            requirement = db.get(RoleSkill,(rid,sid))
            assert requirement and edge['importance'] == requirement.required_importance
            assert edge['source_ids'] == [requirement.source_id]
            assert edge['gap'] == round(1-levels.get(sid,0),2)
            assert edge['critical'] == (requirement.required_importance >= 4)
            if edge['type']=='missing_skill': assert sid in gaps[rid] and edge['gap'] == gaps[rid][sid]['gap']


def test_partial_skills_remain_owned_and_strong_skills_have_no_gap_edges(graph_env):
    client, engine = graph_env
    pid, skills = confirmed(client, engine)
    graph = client.get(URL).json()
    owned_ids = {'skill:'+s['skill_id'] for s in skills}
    assert all(n['type']=='owned_skill' for n in graph['nodes'] if n['id'] in owned_ids)
    assert any(e['type']=='requires_skill' and e['target'] in owned_ids and e['gap']==.35 for e in graph['edges'])
    skills = [{**s,'level':'strong'} for s in skills]
    client.put(f'/api/profiles/{pid}/skills',json={'skills':skills},headers=HEADERS)
    graph = client.get(URL).json()
    assert not any(e['type']=='missing_skill' and e['target'] in owned_ids for e in graph['edges'])


def test_only_reviewed_sdg_records_create_edges(graph_env):
    client, engine = graph_env
    confirmed(client, engine)
    graph = client.get(URL).json()
    links = [e for e in graph['edges'] if e['type']=='contributes_to_target']
    assert links  # Real Science/Instructing links, not invented role relevance.
    with Session(engine) as db:
        for edge in links:
            record = db.get(SDGLink,edge['supporting_id'])
            assert record.curation_status == 'human_reviewed' and record.reviewed_by and record.reviewed_at
            assert edge['rationale'] == record.rationale and edge['target']=='sdg_target:'+record.target_id
            assert edge['source'] == ('role:'+record.role_id if record.role_id else 'skill:'+record.skill_id)
        for record in db.scalars(select(SDGLink)): record.curation_status = 'pending_human_review'
        db.commit()
    unreviewed = client.get(URL).json()
    assert not any(e['type']=='contributes_to_target' for e in unreviewed['edges'])
    assert not any(n['type'] in ('sdg','sdg_target') for n in unreviewed['nodes'])


def test_no_inferred_sdg_links_when_no_matching_review_exists(graph_env):
    client, engine = graph_env
    confirmed(client, engine, ['Writing','Programming'])
    assert not any(e['type']=='contributes_to_target' for e in client.get(URL).json()['edges'])


def test_composition_limits_with_entire_canonical_catalogue(graph_env):
    client, engine = graph_env
    with Session(engine) as db: names = list(db.scalars(select(Skill.canonical_name)))
    confirmed(client, engine, names)
    graph = client.get(URL).json()
    assert len(graph['nodes']) <= MAX_NODES and len(graph['edges']) <= MAX_EDGES
    assert len([n for n in graph['nodes'] if n['type']=='role']) <= MAX_ROLES
    assert len([n for n in graph['nodes'] if n['type']=='owned_skill']) == len(names)
    assert len([e for e in graph['edges'] if e['type']=='missing_skill']) <= MAX_ROLES*MAX_GAPS_PER_ROLE
    assert len([e for e in graph['edges'] if e['type']=='contributes_to_target']) <= MAX_SDG_LINKS
