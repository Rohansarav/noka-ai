"""Smoke test an isolated demo session; never reads or edits an existing user's profile."""
import argparse
import json
import time
import httpx


def verify(url):
    headers={'X-Noka-CSRF':'1','Origin':url}
    result={}
    with httpx.Client(base_url=url,timeout=60) as client:
        assert client.get('/api/ready').status_code==200
        first=client.get('/api/careers?limit=12').json()
        second=client.get('/api/careers?limit=12&offset=12').json()
        assert first['total']>25
        assert not {r['id'] for r in first['roles']} & {r['id'] for r in second['roles']}
        result['catalogue_roles']=first['total']
        hints=client.get('/api/careers',params={'q':'Machine Learning Engineer'}).json()
        assert any(r['id']=='15-2051.00' for r in hints['roles'])
        skills={s['canonical_name']:s['id'] for s in client.get('/api/skills').json()['skills']}
        entries=[{'skill_id':skills[name],'level':'working','years':None} for name in ['Programming','Writing','Critical Thinking']]
        pid=client.post('/api/profiles',json={'is_demo':True},headers=headers).json()['id']
        try:
            draft={'current_field':'Demo computing study','goal':'Analyse data and develop software',
                   'projects':'Illustrative data analysis project','constraints':'Evening study','weekly_hours':7,
                   'skills':entries,'aspirations':[{'title':'Machine Learning Engineer','role_ids':['15-2051.00'],'status':'confirmed'}]}
            saved=client.put(f'/api/profiles/{pid}/skills',json={'skills':entries,'onboarding':draft},headers=headers)
            assert saved.status_code==200, saved.status_code
            for scenario in ['collaboration','governed','acceleration']:
                start=time.monotonic()
                response=client.put('/api/profiles/current/future',json={'scenario':scenario,'role_id':'15-2051.00'},headers=headers)
                assert response.status_code==200
                future=response.json()
                target=next(m for m in future['matches'] if m['role_id']=='15-2051.00')
                assert target['is_target'] and target['score']==target['coverage'] and target['interest_adjustment']==0
                assert future['analysis_context']['aspirations'][0]['title']=='Machine Learning Engineer'
                graph=client.get('/api/profiles/current/career-graph').json()
                gaps={e['target'].removeprefix('skill:') for e in graph['edges'] if e['type']=='missing_skill' and e['source']=='role:15-2051.00'}
                assert gaps=={task['skill_id'] for task in future['pathway'][:3]}
                result[scenario]={'target_retained':True,'readiness':target['score'],'shared_gap_priority':True,'roundtrip_seconds':round(time.monotonic()-start,2)}
            draft['goal']='A draft goal that is not yet confirmed'
            assert client.put(f'/api/profiles/{pid}/onboarding',json=draft,headers=headers).status_code==200
            assert client.get('/api/profiles/current/future').json()['analysis_context']['goal']=='Analyse data and develop software'
            result['draft_isolation']=True
        finally:
            assert client.delete(f'/api/profiles/{pid}',headers=headers).status_code==204
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8010')
    args=parser.parse_args()
    print(json.dumps(verify(args.url.rstrip('/')),indent=2))
