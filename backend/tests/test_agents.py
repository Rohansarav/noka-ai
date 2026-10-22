"""Provider doubles test real orchestration/journalling, never stand in for a live trace."""
import json
from datetime import timedelta
from types import SimpleNamespace as NS
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pydantic import SecretStr
from backend.tests.test_career_graph import graph_env, confirmed, HEADERS
from backend.app.main import app
from backend.app.config import get_settings
from backend.app.models import AgentExecution, AgentEvent, Profile
from backend.app.agents import api, orchestrator
from backend.app.agents.execution import recover, now, locked, event
from backend.app.agents.tools import invoke
from backend.app.matching import match_profile

BASE = '/api/agent-executions'


def prepare(env):
    client, engine = env
    pid, _ = confirmed(client, engine)
    graph = client.get('/api/profiles/current/career-graph').json()
    role = next(n['entity_id'] for n in graph['nodes'] if n['type']=='role')
    return client, engine, pid, graph, role


def start(client, role, **extra):
    return client.post(BASE, json={'question':'Explain the gaps', 'role_id':role, **extra}, headers=HEADERS)


def test_future_context_change_rejects_late_provider_output(graph_env,monkeypatch):
    from backend.app.models import FutureWorkspace
    client,engine,pid,graph,role=prepare(graph_env)
    monkeypatch.setattr(get_settings(),'openai_api_key',SecretStr('test-key-not-real'))
    def change_world(*args,**kwargs):
        with Session(engine) as db:
            workspace=db.get(FutureWorkspace,pid)
            workspace.scenario='governed'
            workspace.updated_at=now()+timedelta(seconds=1)
            db.commit()
        return reply(calls=[call('get_ranked_matches',{})])
    monkeypatch.setattr(orchestrator,'provider',change_world)
    response=start(client,role)
    value=client.get(BASE+'/'+response.json()['id']).json()
    assert value['status']=='failed' and value['error_code']=='profile_changed'
    assert value['result'] is None


def call(name, args):
    return NS(type='function_call', name=name, arguments=json.dumps(args), call_id='call_'+name)


def reply(calls=None, selection=None):
    return NS(output=calls or [], output_text=json.dumps(selection), usage=NS(total_tokens=23))


def final(role, sections=None, **extra):
    return {'sections':sections or ['fit'], 'focus_role':'role:'+role, 'highlight_skills':[], 'open_evidence':None, **extra}


def provider(monkeypatch, responses):
    monkeypatch.setattr(get_settings(), 'openai_api_key', SecretStr('test-key-not-real'))
    iterator = iter(responses)
    def fake(*args, **kwargs):
        assert kwargs['store'] is False and kwargs['parallel_tool_calls'] is False
        assert kwargs['tools'] and all(t['strict'] for t in kwargs['tools'])
        value = next(iterator)
        if isinstance(value, Exception): raise value
        return value
    monkeypatch.setattr(orchestrator, 'provider', fake)


def test_missing_key_ownership_sse_and_no_question_storage(graph_env, monkeypatch, caplog):
    client, engine, pid, graph, role = prepare(graph_env)
    monkeypatch.setattr(get_settings(),'openai_api_key',None)
    response = start(client, role, question='Private Canary Person do not log')
    assert response.status_code == 202
    rid = response.json()['id']
    value = client.get(BASE+'/'+rid).json()
    assert value['status']=='failed' and value['error_code']=='ai_unavailable'
    assert [e['sequence'] for e in value['events']]==[1,2]
    assert 'Private Canary' not in json.dumps(value) + caplog.text
    stream = client.get(BASE+'/'+rid+'/events')
    assert stream.headers['content-type'].startswith('text/event-stream')
    assert 'event: done' in stream.text and 'id: 2' in stream.text
    resumed = client.get(BASE+'/'+rid+'/events',headers={'Last-Event-ID':'1'}).text
    assert 'id: 1\n' not in resumed and 'id: 2' in resumed
    with TestClient(app) as stranger:
        assert stranger.get(BASE+'/'+rid).status_code==404
        assert stranger.get(BASE+'/'+rid+'/events').status_code==404
        assert stranger.post(BASE+'/'+rid+'/cancel',headers=HEADERS).status_code==404
    assert client.post(BASE, json={'role_id':role,'question':'abc'}).status_code==403
    assert start(client, role, agent='scout').status_code==422
    assert start(client, 'made-up-role').status_code==422
    assert start(client, role, profile_id=pid).status_code==422


def test_tool_loop_completes_with_authoritative_scores(graph_env, monkeypatch):
    client, engine, pid, graph, role = prepare(graph_env)
    provider(monkeypatch, [reply([call('get_ranked_matches',{})]), reply(selection=final(role))])
    rid = start(client,role).json()['id']
    value = client.get(BASE+'/'+rid).json()
    assert value['status']=='completed' and value['tool_count']==1 and value['token_usage']==46
    assert [e['type'] for e in value['events']]==['queued','running','tool_completed','completed']
    with Session(engine) as db:
        expected = next(m for m in match_profile(db.get(Profile,pid),db)['matches'] if m['role_id']==role)
    assert value['result']['sections'][0]['data']==expected
    assert all('test-key' not in str(e) for e in value['events'])


def test_model_can_choose_gaps_first_and_highlight_retrieved_skill(graph_env,monkeypatch):
    client, engine, pid, graph, role=prepare(graph_env)
    with Session(engine) as db:
        gaps=invoke('get_skill_gaps',json.dumps({'role_id':role}),db.get(Profile,pid),db,{role})
    node_ids={n['id'] for n in graph['nodes']}
    skill=next('skill:'+g['skill_id'] for g in gaps if 'skill:'+g['skill_id'] in node_ids)
    provider(monkeypatch,[reply([call('get_skill_gaps',{'role_id':role})]),reply(selection=final(role,sections=['gaps'],highlight_skills=[skill]))])
    rid=start(client,role).json()['id']
    value=client.get(BASE+'/'+rid).json()
    assert value['status']=='completed' and value['tool_count']==1
    assert value['events'][2]['payload']['tool']=='get_skill_gaps'
    assert value['result']['sections'][0]['data']==gaps
    assert value['result']['effects']['highlight_skills']==[skill]


def test_generation_schema_uses_exact_graph_and_retrieved_references(graph_env):
    client, engine, pid, graph, role=prepare(graph_env)
    from backend.app.career_graph import build_career_graph
    from backend.app.agents.registry import definitions
    with Session(engine) as db:
        profile=db.get(Profile,pid)
        current=build_career_graph(profile,db)
        initial=orchestrator.selection_schema(current,role,{})['properties']
        assert initial['focus_role']['enum']==['role:'+role]
        assert initial['highlight_skills']['maxItems']==0
        assert initial['open_evidence']=={'type':'null'}
        gaps=invoke('get_skill_gaps',json.dumps({'role_id':role}),profile,db,{role})
        constrained=orchestrator.selection_schema(current,role,{('get_skill_gaps',role):gaps})['properties']
        assert constrained['sections']['items']['enum']==['gaps']
        allowed={n.id for n in current.nodes if n.type in {'owned_skill','required_skill'}}
        assert set(constrained['highlight_skills']['items']['enum']) <= allowed
        assert set(constrained['highlight_skills']['items']['enum']) <= {'skill:'+g['skill_id'] for g in gaps}
    for tool in definitions({role}):
        if 'role_id' in tool['parameters']['properties']:
            assert tool['parameters']['properties']['role_id']['enum']==[role]


@pytest.mark.parametrize('tool,args', [('delete_profile',{}),('get_current_profile',{'profile_id':'other'}),('get_role_requirements',{'role_id':'other'}),('get_ranked_matches',{'extra':True})])
def test_reject_unauthorized_tool_and_args(graph_env,monkeypatch,tool,args):
    client, engine, pid, graph, role = prepare(graph_env)
    provider(monkeypatch,[reply([call(tool,args)])])
    rid=start(client,role).json()['id']
    assert client.get(BASE+'/'+rid).json()['status']=='failed'


@pytest.mark.parametrize('selection', [lambda r:final(r,score=99), lambda r:final(r,highlight_skills=['skill:fake']), lambda r:final(r,sections=['sdgs']),lambda r:final('other')])
def test_reject_fabricated_or_unsupported_result(graph_env,monkeypatch,selection):
    client, engine, pid, graph, role=prepare(graph_env)
    provider(monkeypatch,[reply([call('get_ranked_matches',{})]),reply(selection=selection(role))])
    rid=start(client,role).json()['id']
    result=client.get(BASE+'/'+rid).json()
    assert result['status']=='failed' and result['result'] is None


def test_cancel_recovery_quota_and_delete_cascade(graph_env,monkeypatch):
    client, engine, pid, graph, role=prepare(graph_env)
    monkeypatch.setattr(api,'execute',lambda *args:None)
    monkeypatch.setattr(get_settings(),'agent_daily_quota',2)
    rid=start(client,role).json()['id']
    assert client.post(BASE+'/'+rid+'/cancel',headers=HEADERS).json()['status']=='cancelled'
    assert client.post(BASE+'/'+rid+'/cancel',headers=HEADERS).json()['events'][-1]['sequence']==2
    rid2=start(client,role).json()['id']
    with Session(engine) as db:
        run=locked(db,rid2); run.deadline=now()-timedelta(seconds=1); db.commit()
    value=client.get(BASE+'/'+rid2).json()
    assert value['status']=='failed' and value['error_code']=='deadline_or_interrupted'
    assert start(client,role).status_code==429
    assert client.delete('/api/profiles/'+pid,headers=HEADERS).status_code==204
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AgentExecution))==0
        assert db.scalar(select(func.count()).select_from(AgentEvent))==0


def test_concurrent_limit_provider_failure_and_tool_budget(graph_env,monkeypatch):
    client, engine, pid, graph, role=prepare(graph_env)
    provider(monkeypatch,[TimeoutError('private provider detail')])
    rid=start(client,role).json()['id']
    assert client.get(BASE+'/'+rid).json()['error_code']=='timeout'
    monkeypatch.setattr(get_settings(),'agent_max_tools',0)
    provider(monkeypatch,[reply([call('get_ranked_matches',{})])])
    rid=start(client,role).json()['id']
    assert client.get(BASE+'/'+rid).json()['error_code']=='tool_limit'
    monkeypatch.setattr(api,'execute',lambda *args:None)
    monkeypatch.setattr(get_settings(),'agent_max_concurrent',1)
    assert start(client,role).status_code==202
    assert start(client,role).status_code==429


def test_turn_deadline_global_limits_and_body_bounds(graph_env,monkeypatch):
    client, engine, pid, graph, role=prepare(graph_env)
    monkeypatch.setattr(get_settings(),'agent_max_turns',1)
    provider(monkeypatch,[reply([call('get_current_profile',{})])])
    rid=start(client,role).json()['id']
    assert client.get(BASE+'/'+rid).json()['error_code']=='turn_limit'
    monkeypatch.setattr(get_settings(),'agent_max_turns',4)
    def late(*args,**kwargs):
        with Session(engine) as db:
            run=db.scalar(select(AgentExecution).where(AgentExecution.status=='running'))
            run.deadline=now()-timedelta(seconds=1);db.commit()
        return reply(selection=final(role))
    monkeypatch.setattr(orchestrator,'provider',late)
    rid=start(client,role).json()['id']
    assert client.get(BASE+'/'+rid).json()['error_code']=='timeout'
    monkeypatch.setattr(api,'execute',lambda *args:None)
    monkeypatch.setattr(get_settings(),'agent_global_concurrent',1)
    assert start(client,role).status_code==202
    with TestClient(app) as other:
        _, _ = confirmed(other,engine)
        assert start(other,role).status_code==429
    assert client.post(BASE,content=b'x'*9000,headers=HEADERS).status_code==413


def test_tools_use_reviewed_attributed_records_and_confirmed_fields(graph_env):
    client, engine, pid, graph, role=prepare(graph_env)
    with Session(engine) as db:
        profile=db.get(Profile,pid)
        assert invoke('get_current_profile','{}',profile,db,{role})['confirmed'] is True
        assert all('skill_id' in s and 'level' in s for s in invoke('get_confirmed_skills','{}',profile,db,{role}))
        requirements=invoke('get_role_requirements',json.dumps({'role_id':role}),profile,db,{role})
        assert requirements and all(r['source_id'] and r['importance']>0 for r in requirements)
        evidence=invoke('get_role_evidence',json.dumps({'role_id':role}),profile,db,{role})
        assert evidence['url'].startswith('https://') and 'no individual-role forecast' in evidence['limitation']
        links=invoke('get_reviewed_sdg_connections',json.dumps({'role_id':role}),profile,db,{role})
        assert links and all(l['source_id'] and l['rationale'] and (l['role_id'] or l['skill_id']) for l in links)


def test_cancellation_wins_over_inflight_provider(graph_env,monkeypatch):
    client, engine, pid, graph, role=prepare(graph_env)
    monkeypatch.setattr(get_settings(),'openai_api_key',SecretStr('test'))
    def cancel_during_provider(*args,**kwargs):
        with Session(engine) as db:
            rid=db.scalar(select(AgentExecution.id))
            run=locked(db,rid);run.status='cancelled';event(db,run,'cancelled');db.commit()
        return reply(selection=final(role))
    monkeypatch.setattr(orchestrator,'provider',cancel_during_provider)
    rid=start(client,role).json()['id']
    value=client.get(BASE+'/'+rid).json()
    assert value['status']=='cancelled' and value['result'] is None


def test_cancel_handles_execution_removed_before_lock(graph_env,monkeypatch):
    client, engine, pid, graph, role=prepare(graph_env)
    monkeypatch.setattr(api,'execute',lambda *args:None)
    rid=start(client,role).json()['id']
    monkeypatch.setattr(api,'locked',lambda *args:None)
    assert client.post(BASE+'/'+rid+'/cancel',headers=HEADERS).status_code==404


def test_guide_routes_and_records_its_own_model(graph_env, monkeypatch):
    client, engine, _, _, role = prepare(graph_env)
    settings = get_settings()
    monkeypatch.setattr(settings, 'openai_api_key', SecretStr('test-key'))
    monkeypatch.setattr(settings, 'openai_extraction_model', 'extraction-only')
    monkeypatch.setattr(settings, 'openai_guide_model', 'guide-only')
    monkeypatch.setattr(settings, 'openai_model', 'scout-only')
    responses = iter([reply([call('get_ranked_matches', {})]), reply(selection=final(role))])
    seen = []
    def fake(*args, **kwargs):
        seen.append(kwargs['model'])
        return next(responses)
    monkeypatch.setattr(orchestrator, 'provider', fake)
    rid = start(client, role).json()['id']
    assert client.get(BASE+'/'+rid).json()['status'] == 'completed'
    assert seen == ['guide-only', 'guide-only']
    with Session(engine) as db:
        assert db.get(AgentExecution, rid).model == 'guide-only'
