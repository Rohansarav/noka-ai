"""Isolated demo smoke test for specific skills, real provider extraction and reviewed SDG paths."""
import argparse
import json
import time
import httpx


def verify(url,use_ai):
    headers={'X-Noka-CSRF':'1','Origin':url}
    report={}
    with httpx.Client(base_url=url,timeout=90) as client:
        assert client.get('/api/ready').status_code==200
        catalogue=client.get('/api/skill-catalogue?limit=1').json()
        assert catalogue['counts']['software']>1000 and catalogue['counts']['core']==35
        report['catalogue']=catalogue['counts'];report['total_skills']=catalogue['catalogue_total']
        def skill(q):
            result=client.get('/api/skill-catalogue',params={'q':q,'category':'software'}).json()['skills']
            return next(s for s in result if q.casefold() in {s['canonical_name'].casefold(),*(a.casefold() for a in s['aliases'])})
        values={q:skill(q) for q in ['Python','SQL','JS','CSS','HTML']}
        pid=client.post('/api/profiles',json={'is_demo':True},headers=headers).json()['id']
        try:
            print('Checking bounded extraction with demo experience.',flush=True)
            response=client.post(f'/api/profiles/{pid}/analysis',data={'use_ai':str(use_ai).lower(),'text':'I used Python and SQL to analyse project data. I also used JavaScript, CSS and HTML to build a project interface.'},headers=headers)
            assert response.status_code==200
            extraction=response.json()
            found={sid for item in extraction['candidates'] for sid in item['options']}
            assert values['Python']['id'] in found and values['SQL']['id'] in found
            report['extraction_mode']=extraction['mode']
            def save(names):
                entries=[{'skill_id':values[name]['id'],'level':'working'} for name in names]
                draft={'current_field':'Demo computing study','goal':'Explore software and data careers','skills':entries,'interests':['15-2051.00','15-1252.00']}
                response=client.put(f'/api/profiles/{pid}/skills',json={'skills':entries,'interests':draft['interests'],'onboarding':draft},headers=headers)
                assert response.status_code==200
            save(['Python','SQL','JS'])
            start=time.monotonic()
            future=client.get('/api/profiles/current/future').json()
            data=next(m for m in future['matches'] if m['role_id']=='15-2051.00')
            assert data['technical']['matched_count']==3 and data['score']==0 and data['readiness_status']=='not_assessed'
            graph=client.get('/api/profiles/current/career-graph').json()
            ids={node['id'] for node in graph['nodes']}
            assert all(edge['source'] in ids and edge['target'] in ids for edge in graph['edges'])
            reviewed=[edge for edge in graph['edges'] if edge['type']=='contributes_to_target']
            assert reviewed and all(edge['review_status']=='human_reviewed' and edge['rationale'] and edge['source_ids'] for edge in reviewed)
            contexts={edge['target'] for edge in graph['edges'] if edge['source']=='role:15-2051.00' and edge['type']=='context_requirement'}
            assert any(edge['source'] in contexts for edge in reviewed)
            assert any(edge['type']=='uses_technology' and edge['importance'] is None and edge['gap'] is None for edge in graph['edges'])
            report['data_profile']={'matched_tools':data['technical']['matched_count'],'broad_readiness':'not_assessed','reviewed_sdg_paths':len(reviewed),'context_chain':True,'future_and_graph_seconds':round(time.monotonic()-start,2)}
            save(['JS','CSS','HTML'])
            changed=client.get('/api/profiles/current/future').json()
            web=next(m for m in changed['matches'] if m['role_id']=='15-1252.00')
            data=next(m for m in changed['matches'] if m['role_id']=='15-2051.00')
            assert web['technical']['matched_count']==3 and data['technical']['matched_count']==1
            assert web['score']==data['score']==0
            report['web_profile']={'software_developer_tools':3,'data_scientist_tools':1,'no_broad_score_inflation':True}
        finally:
            assert client.delete(f'/api/profiles/{pid}',headers=headers).status_code==204
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8010')
    parser.add_argument('--use-ai',action='store_true',help='Send only the embedded illustrative experience to the configured OpenAI provider')
    args=parser.parse_args()
    print(json.dumps(verify(args.url.rstrip('/'),args.use_ai),indent=2))
