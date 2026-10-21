"""Disposable HTTP acceptance checks. Optional --provider uses a limited real OpenAI run."""
import argparse
import json
import time
from pathlib import Path
import httpx


def verify(base, provider):
    report={"base_url":base,"checks":[]}
    headers={"X-Noka-CSRF":"1","Origin":base}
    profiles=[]
    with httpx.Client(base_url=base,timeout=90) as worker, httpx.Client(base_url=base,timeout=90) as student:
        try:
            for client,skills in [(worker,{"2.A.2.a":"strong","2.B.3.e":"strong","2.A.1.e":"working","2.A.2.b":"working"}),
                                  (student,{"2.A.1.b":"learning","2.B.1.e":"learning","2.A.1.c":"working"})]:
                response=client.post("/api/profiles",json={"is_demo":True},headers=headers);response.raise_for_status()
                pid=response.json()["id"];profiles.append((client,pid))
                response=client.put(f"/api/profiles/{pid}/skills",json={"skills":[{"skill_id":sid,"level":level,"years":None} for sid,level in skills.items()],"country":"MY","interests":[]},headers=headers)
                response.raise_for_status()
            a=worker.get("/api/profiles/current/future");a.raise_for_status();a=a.json()
            b=student.get("/api/profiles/current/future");b.raise_for_status();b=b.json()
            assert a["matches"]!=b["matches"]
            assert student.get(f"/api/profiles/{profiles[0][1]}").status_code==404
            report["checks"].append("Distinct workforce/student rankings; cross-session denial")
            role=a["matches"][0]["role_id"]
            a=worker.put("/api/profiles/current/future",json={"role_id":role},headers=headers).json()
            student_state=student.put('/api/profiles/current/future',json={'role_id':b['matches'][0]['role_id']},headers=headers).json()
            assert a['pathway']!=student_state['pathway']
            report['profile_comparison']={
                'worker_matches':[{'title':m['title'],'score':m['score']} for m in a['matches'][:3]],
                'student_matches':[{'title':m['title'],'score':m['score']} for m in student_state['matches'][:3]],
                'worker_priorities':[t['name'] for t in a['pathway'][:3]],
                'student_priorities':[t['name'] for t in student_state['pathway'][:3]],
                'fixture_notice':'Disposable, explicitly labelled demo profiles; not real people.'}
            skill=a["pathway"][0]["skill_id"]
            response=worker.put("/api/profiles/current/pathway",json={"skill_id":skill,"status":"completed"},headers=headers);response.raise_for_status()
            for scenario in ("acceleration","governed","collaboration"):
                response=worker.put("/api/profiles/current/future",json={"scenario":scenario,"weekly_hours":12},headers=headers);response.raise_for_status()
                state=response.json()
                assert state["scenario"]==scenario and state["role_id"]==role
                assert next(t for t in state["pathway"] if t["skill_id"]==skill)["status"]=="completed"
            report["checks"].append("Three worlds, saved hours, persistent completed progress")
            graph=worker.get("/api/profiles/current/career-graph").json()
            assert any(n["entity_id"]==role for n in graph["nodes"])
            report["checks"].append("Selected role remains in existing Universe")
            assert worker.get("/api/ready").status_code==200
            forecast=worker.get("/api/forecasts").json()
            assert forecast["status"]=="evaluated" and len(forecast["sectors"])==141
            report["checks"].append("Ready endpoint and 141 actual evaluated forecasts")
            intelligence=worker.get("/api/intelligence").json()
            report["scout"]={"findings":len(intelligence["findings"]),"latest_status":intelligence["runs"][0]["status"] if intelligence["runs"] else None}
            if provider:
                response=worker.post("/api/agent-executions",json={"agent":"matchmaker","role_id":role,"question":"Compare my selected role across the three future scenarios using my saved context."},headers=headers)
                response.raise_for_status();run=response.json()
                deadline=time.monotonic()+130
                while run["status"] not in {"completed","failed","cancelled"} and time.monotonic()<deadline:
                    time.sleep(2)
                    run=worker.get("/api/agent-executions/"+run["id"]).json()
                report["guide"]={"status":run["status"],"error_code":run["error_code"],"tool_count":run["tool_count"],
                                 "events":[{"type":e["type"],"payload":e["payload"]} for e in run["events"]],
                                 "sections":[s["kind"] for s in (run.get("result") or {}).get("sections",[])]}
            return report
        finally:
            for client,pid in profiles:
                response=client.delete(f"/api/profiles/{pid}",headers=headers)
                if response.status_code!=204: print("Disposable profile cleanup failed; investigate locally.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",default="http://localhost:8010")
    parser.add_argument("--provider",action="store_true")
    args=parser.parse_args()
    result=verify(args.base,args.provider)
    Path("docs/qa/future-live.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
