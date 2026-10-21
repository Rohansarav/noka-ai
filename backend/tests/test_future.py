"""Integrated workspace, temporal integrity and research safety regression tests."""
import json
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.models import Base, FutureWorkspace, Skill
from backend.app.evidence_api import get_session
from backend.app.ingestion.runner import import_all
from backend.app.scout import canonical, refresh
from backend.app.outlooks import refresh_outlooks
from ml.train import features
from backend.app.config import Settings

HEADERS={"X-Noka-CSRF":"1","Origin":"http://testserver"}


@pytest.fixture
def clients():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    @event.listens_for(engine,"connect")
    def fk(conn,record): conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    import_all(engine,Path("data/fixtures"),offline=True)
    def session():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_session]=session
    with TestClient(app) as first, TestClient(app) as second:
        yield first,second,engine
    app.dependency_overrides.clear()
    engine.dispose()


def profile(client,levels):
    pid=client.post("/api/profiles",json={"is_demo":True},headers=HEADERS).json()["id"]
    body={"skills":[{"skill_id":sid,"level":level,"years":None} for sid,level in levels.items()],"country":"MY","interests":[]}
    assert client.put(f"/api/profiles/{pid}/skills",json=body,headers=HEADERS).status_code==200
    return pid


def test_worlds_progress_and_isolation(clients):
    a,b,engine=clients
    pid=profile(a,{"2.A.2.a":"strong","2.B.3.e":"working","2.A.1.e":"working"})
    profile(b,{"2.A.1.b":"learning","2.B.1.e":"learning","2.A.1.c":"working"})
    worker=a.get("/api/profiles/current/future").json()
    student=b.get("/api/profiles/current/future").json()
    assert worker["matches"]!=student["matches"]
    assert b.get(f"/api/profiles/{pid}").status_code==404
    role=worker["matches"][0]["role_id"]
    chosen=a.put("/api/profiles/current/future",json={"role_id":role},headers=HEADERS).json()
    task=chosen["pathway"][0]["skill_id"]
    assert a.put("/api/profiles/current/pathway",json={"skill_id":task,"status":"completed","note":"My fixture portfolio reflection"},headers=HEADERS).status_code==200
    notes_only=a.put('/api/profiles/current/pathway',json={'skill_id':task,'note':'My fixture portfolio reflection'},headers=HEADERS).json()
    assert next(t for t in notes_only['pathway'] if t['skill_id']==task)['status']=='completed'
    for scenario in ("governed","acceleration","collaboration"):
        changed=a.put("/api/profiles/current/future",json={"scenario":scenario,"weekly_hours":12},headers=HEADERS).json()
        assert changed["role_id"]==role and changed["weekly_hours"]==12
        assert next(t for t in changed["pathway"] if t["skill_id"]==task)["status"]=="completed"
        assert next(t for t in changed["pathway"] if t["skill_id"]==task)["note"]=="My fixture portfolio reflection"
        assert changed["scenarios"][scenario]["name"] in changed["future_self"]
        from backend.app.matching import match_profile
        from backend.app.models import Profile
        with Session(engine) as db:
            all_scores = {m['role_id']:m['score'] for m in match_profile(db.get(Profile,pid),db,limit=None)['matches']}
        assert all(m['score']==all_scores[m['role_id']] for m in changed['matches'])
        assert role in {m['role_id'] for m in changed['matches']}
        assert a.get("/api/profiles/current/future").json()["scenario"]==scenario
    assert b.get("/api/profiles/current/future").json()["role_id"] is None
    assert a.delete(f"/api/profiles/{pid}",headers=HEADERS).status_code==204
    with Session(engine) as db: assert db.get(FutureWorkspace,pid) is None


def test_workspace_validation(clients):
    a,b,_=clients
    profile(a,{"2.A.2.a":"strong","2.B.3.e":"working","2.A.1.e":"working"})
    assert b.get("/api/profiles/current/future").status_code==404
    for body in ({"weekly_hours":0},{"scenario":"utopia"},{"role_id":"invented"},{"profile_id":"other"}):
        assert a.put("/api/profiles/current/future",json=body,headers=HEADERS).status_code==422
    assert a.put("/api/profiles/current/future",json={"weekly_hours":10}).status_code==403
    assert a.put("/api/profiles/current/pathway",json={"skill_id":"invented","status":"completed"},headers=HEADERS).status_code==422
    role=a.get('/api/profiles/current/future').json()['matches'][0]['role_id']
    assert a.post('/api/agent-executions',json={'role_id':role,'node_id':'skill:invented','question':'Explain this node'},headers=HEADERS).status_code==422


def test_features_and_model_time_integrity():
    series=pd.Series(range(120),dtype=float)
    altered=series.copy();altered.iloc[90:]=99999
    pd.testing.assert_frame_equal(features(series).iloc[:90],features(altered).iloc[:90])
    path=Path("ml/artifacts/evaluation.json")
    if not path.exists(): pytest.skip("Run actual training for artifact audit")
    report=json.loads(path.read_text())
    with TestClient(app) as client:
        response=client.get("/api/forecasts")
        assert response.status_code==200 and response.json()["status"]=="evaluated"
    assert len(report["sectors"])==141
    for row in report["sectors"]:
        selection,holdout=row["backtests"][:5],row["backtests"][5:]
        assert max(r["target_date"] for r in selection)<=min(r["origin"] for r in holdout)
        assert row["metrics"]["selected"]["n"]==3


def test_missing_search_key_and_url_safety(clients,monkeypatch):
    from backend.app import scout
    monkeypatch.setattr(scout,"get_settings",lambda:Settings(tavily_api_key=None))
    result=refresh(clients[2])
    assert result["status"]=="unavailable" and not result["events"]
    assert canonical("file:///etc/passwd") is None
    assert canonical("https://example.org/path?token=private#section")=="https://example.org/path"
    assert canonical("https://example.org/document?id=42&utm_source=tracking")=="https://example.org/document?id=42"


def test_outlook_and_impact_honesty(clients):
    a,_,engine=clients
    with Session(engine) as db: refresh_outlooks(db)
    rows=a.get("/api/intelligence").json()["outlooks"]
    assert len(rows)==60
    assert next(r for r in rows if r["entity_id"]=="13-2011.00")["category"]=="declining"
    assert all(r["local_category"]=="insufficient_evidence" for r in rows)
    assert all(r["sources"] for r in rows if r["category"]!="insufficient_evidence")
    links=a.get("/api/impact/15-1252.00").json()["relationships"]
    assert all(l["target_id"] and l["url"].startswith("https://") for l in links)
    nursing=a.get("/api/impact/29-1141.00").json()["relationships"]
    assert any(l["target_id"]=="3.c" and l["status"]=="Curated SDG relationship" for l in nursing)
