"""Onboarding uses the existing owner/session boundary and never changes profile facts by world."""
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.tests.test_profiles import database, client, create, payload, HEADERS


def test_draft_resume_completion_and_scenario_facts(client, database):
    pid=create(client)
    data=payload(database)
    draft={"step":2,"status":"student","current_field":"Demo computer science","country":"SG","market":"MY","goal":"Build useful tools","weekly_hours":12,"skills":data["skills"]}
    response=client.put(f"/api/profiles/{pid}/onboarding",json=draft,headers=HEADERS)
    assert response.status_code==200
    profile=client.get('/api/profiles/current').json()['profile']
    assert profile['onboarding']['step']==2 and profile['skills']==[] and not profile['confirmed']
    assert client.put(f"/api/profiles/{pid}/skills",json={**data,"onboarding":draft},headers=HEADERS).status_code==200
    before=client.get('/api/profiles/current').json()
    assert before['profile']['onboarding']['completed'] is True
    assert client.get('/api/profiles/current/future').json()['weekly_hours']==12
    assert client.get('/api/profiles/current/future').json()['role_id']
    graph=client.get('/api/profiles/current/career-graph').json()
    graph.pop('generated_at')
    research=client.get('/api/intelligence').json()
    impact=client.get('/api/impact/'+client.get('/api/profiles/current/future').json()['role_id']).json()
    for world in ('governed','acceleration','collaboration'):
        response=client.put('/api/profiles/current/future',json={'scenario':world},headers=HEADERS)
        assert response.status_code==200 and response.json()['scenario']==world
        assert client.get('/api/profiles/current').json()==before
        current_graph=client.get('/api/profiles/current/career-graph').json()
        current_graph.pop('generated_at')
        assert current_graph==graph
        assert client.get('/api/intelligence').json()==research
        assert client.get('/api/impact/'+response.json()['role_id']).json()==impact


def test_drafts_are_owned_bounded_and_csrf_protected(client, database):
    pid=create(client)
    with TestClient(app) as other:
        assert other.put(f"/api/profiles/{pid}/onboarding",json={},headers=HEADERS).status_code==404
    assert client.put(f"/api/profiles/{pid}/onboarding",json={}).status_code==403
    for body in ({'resume':'never saved'}, {'weekly_hours':41}, {'step':3}, {'skills':[{'skill_id':'fake'}]}):
        assert client.put(f"/api/profiles/{pid}/onboarding",json=body,headers=HEADERS).status_code==422


def test_completion_requires_reviewed_skills_and_legacy_profiles_stay_complete(client, database):
    pid=create(client)
    data=payload(database)
    assert client.put(f"/api/profiles/{pid}/skills",json={**data,'skills':data['skills'][:2],'onboarding':{'current_field':'Test'}},headers=HEADERS).status_code==422
    response=client.put(f"/api/profiles/{pid}/skills",json=data,headers=HEADERS)
    assert response.json()['confirmed'] is True and response.json()['onboarding'] is None
