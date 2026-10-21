"""Exercise scoring, shared worlds and connected pathway persistence in an isolated demo session."""
import argparse
import json
import httpx


def verify(url):
    headers={'X-Noka-CSRF':'1','Origin':url}
    with httpx.Client(base_url=url,timeout=90) as client:
        assert client.get('/api/ready').status_code==200
        response=client.post('/api/profiles',json={'is_demo':True},headers=headers)
        response.raise_for_status()
        pid=response.json()['id']
        try:
            entries=[{'skill_id':sid,'level':level} for sid,level in [('2.A.2.a','strong'),('2.B.3.e','working'),('2.A.1.e','working')]]
            response=client.put(f'/api/profiles/{pid}/skills',json={'skills':entries,'interests':['15-1252.00']},headers=headers)
            response.raise_for_status()
            reports={}
            for scenario in ['acceleration','governed','collaboration']:
                response=client.put('/api/profiles/current/future',json={'role_id':'15-1252.00','scenario':scenario,'weekly_hours':6},headers=headers)
                response.raise_for_status()
                data=response.json()
                assert data['version']=='connected-planning-2026-10-21-v4'
                match=next(m for m in data['matches'] if m['role_id']=='15-1252.00')
                assessment=match['assessment']
                assert assessment['status']=='partial'
                assert abs(match['score']-assessment['evidence_completeness']*assessment['assessed_proficiency']/100)<0.15
                tasks=data['pathway']
                assert 0<len(tasks)<=5 and tasks[0]['dependencies']==[]
                for index,task in enumerate(tasks):
                    assert 1<=task['start_week']<=task['end_week']
                    if index:assert task['dependencies']==[tasks[index-1]['skill_id']]
                persisted=client.get('/api/profiles/current/future').json()
                assert persisted['scenario']==scenario and persisted['role_id']=='15-1252.00'
                graph=client.get('/api/profiles/current/career-graph').json()
                priorities={e['target'][6:] for e in graph['edges'] if e['source']=='role:15-1252.00' and e['type']=='missing_skill'}
                assert priorities=={t['skill_id'] for t in tasks[:3]}
                reports[scenario]={'coverage':match['score'],'recorded_requirements':assessment['recorded_count'],'total_requirements':assessment['required_count'],'pathway_order':[t['name'] for t in tasks]}
            assert len({r['coverage'] for r in reports.values()})==1
            skill=data['pathway'][0]['skill_id']
            assert client.put('/api/profiles/current/pathway',json={'skill_id':skill,'status':'completed'},headers=headers).status_code==422
            response=client.put('/api/profiles/current/pathway',json={'skill_id':skill,'status':'completed','note':'Demo case study tested; feedback and limitations documented.'},headers=headers)
            response.raise_for_status()
            saved=client.get('/api/profiles/current/future').json()
            assert next(t for t in saved['pathway'] if t['skill_id']==skill)['status']=='completed'
            assert all(t['end_week']>=t['start_week']>=1 for t in saved['pathway'])
            return {'scenarios':reports,'progress_persisted':True,'completion_evidence_required':True,'graph_pathway_consistent':True}
        finally:
            assert client.delete(f'/api/profiles/{pid}',headers=headers).status_code==204


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8010')
    args=parser.parse_args()
    print(json.dumps(verify(args.url.rstrip('/')),indent=2))
