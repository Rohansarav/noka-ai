from types import SimpleNamespace as NS
import pytest
from pydantic import SecretStr
from backend.app.matching import discovery_relevance, select_directions
from backend.app.work_changes import interpret, WorkChange, _cache
from backend.app.agents.registry import TOOLS
from backend.tests.test_profiles import database, client, create, HEADERS


def req(ids):
    return [(NS(required_importance=4), NS(id=i, canonical_name=i, category='essential')) for i in ids]


def test_sparse_high_coverage_and_generic_skills_do_not_qualify():
    role=NS(occupation_code='51-6031.00')
    generic=['2.A.1.a','2.A.1.b','2.A.2.a']
    tech={'matched_count':0,'matched':[]}
    assert discovery_relevance(role,req(generic),[],dict.fromkeys(generic,1),tech)==(0,[])
    assert discovery_relevance(role,req(generic[:1]),[],dict.fromkeys(generic,1),tech)==(0,[])
    rows=[{'role_id':'unrelated','title':'Unrelated','is_target':False,'score':100,'discovery_relevance':0},
          {'role_id':'target','title':'Target','is_target':True,'score':0,'discovery_relevance':0}]
    assert [r['role_id'] for r in select_directions(rows)]==['target']


def test_adjacent_family_requires_shared_requirements_and_ranks_without_coverage():
    ids={'2.A.1.a','2.B.3.e','2.B.4.g'}
    target=NS(occupation_code='15-1252.00',title='Software Developers')
    score,reasons=discovery_relevance(NS(occupation_code='15-1242.00'),req(ids),[(target,ids)],{}, {'matched_count':0})
    assert score>0 and 'Software Developers' in reasons[0]
    assert discovery_relevance(NS(occupation_code='51-6031.00'),req(ids),[(target,ids)],{}, {'matched_count':0})==(0,[])
    rows=[{'role_id':'a','title':'A','is_target':False,'score':100,'discovery_relevance':2},
          {'role_id':'b','title':'B','is_target':False,'score':1,'discovery_relevance':3}]
    assert select_directions(rows)[0]['role_id']=='b'


@pytest.mark.parametrize('ids,explanation,status', [([], 'Unsupported prose', 'unavailable'),(['invented'],'Invented citation','unavailable'),(['claim'],'Tasks may change.','suggestion')])
def test_interpretation_never_approves_and_rejects_unknown_citations(monkeypatch,ids,explanation,status):
    _cache.clear()
    seen=[]
    class Provider:
        def __init__(self,**kwargs):self.responses=self
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def parse(self,**kwargs):
            seen.append(kwargs)
            return NS(status='completed',output_parsed=WorkChange(label='transforming',explanation=explanation,source_ids=ids))
    monkeypatch.setattr('openai.OpenAI',Provider)
    outlook={'dimensions':{'change':{'status':'supported'}},'market':'MY','evidence':[{'id':'claim','dimension':'change','category':'transforming','current':True,'statement':'Task evidence','market':'Global','observation_period':'2025','state':'published','locator':'Page 1'}]}
    settings=NS(openai_api_key=SecretStr('test'),openai_model='test')
    result=interpret(NS(title='Developer',description='Builds software'),outlook,settings)
    assert result['status']==status
    if status=='suggestion':
        assert result['review_status']=='pending_review'
        assert result['notice']=='LLM suggestion, needs reviewed evidence'
        assert result['explanation']==(explanation if ids else '')
        assert interpret(NS(title='Developer',description='Builds software'),outlook,settings)==result
        assert len(seen)==1


def test_missing_ai_and_retired_forecast_tool():
    assert interpret(None,None,NS(openai_api_key=None))['status']=='unavailable'
    assert 'get_forecast_context' not in TOOLS


@pytest.mark.parametrize('status,dimension,current', [('insufficient_evidence','change',True),('supported','availability',True),('supported','change',False)])
def test_no_work_change_evidence_never_calls_provider(monkeypatch,status,dimension,current):
    def forbidden(**kwargs):
        pytest.fail('Provider must not be called without current reviewed change evidence')
    monkeypatch.setattr('openai.OpenAI',forbidden)
    outlook={'dimensions':{'change':{'status':status}},'evidence':[{'id':'shortage','current':current,'dimension':dimension,'category':'reported_shortage'}]}
    result=interpret(None,outlook,NS(openai_api_key=SecretStr('test')))
    assert result['status']=='unavailable' and 'label' not in result


def test_work_change_endpoint_requires_session_and_csrf_and_preserves_scope(client, monkeypatch):
    path='/api/opportunities/roles/15-1252.00/work-changes'
    assert client.post(path,headers=HEADERS).status_code==401
    create(client)
    assert client.post(path).status_code==403
    assert client.post(path+'?market=invalid',headers=HEADERS).status_code==422
    assert client.post('/api/opportunities/roles/missing/work-changes',headers=HEADERS).status_code==404
    seen=[]
    monkeypatch.setattr('backend.app.work_changes.interpret',lambda role,outlook,settings: seen.append((role.id,outlook['market'])) or {'status':'unavailable','message':'Fixture'})
    assert client.post(path+'?market=SG',headers=HEADERS).status_code==200
    assert seen==[('15-1252.00','SG')]


def test_interpretation_request_limit(monkeypatch):
    from backend.app.work_changes import allow_request, _usage
    _usage.clear()
    monkeypatch.setattr('backend.app.work_changes.time.monotonic',lambda:100)
    assert all(allow_request('test-session') for _ in range(10))
    assert not allow_request('test-session')
    monkeypatch.setattr('backend.app.work_changes.time.monotonic',lambda:3701)
    assert allow_request('test-session')
