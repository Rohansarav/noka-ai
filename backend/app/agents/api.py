import asyncio
import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.evidence_api import get_session
from backend.app.profile_security import same_origin
from backend.app.career_graph import build_career_graph
from backend.app.agents.contracts import StartExecution
from backend.app.agents.execution import create, owned, owner_profile, snapshot, recover, locked, event, TERMINAL
from backend.app.agents.orchestrator import execute
from backend.app.skill_extraction import clean_text
from backend.app.future import private

router = APIRouter(prefix="/api/agent-executions", tags=["Private agent executions"])


@router.post("", status_code=202, dependencies=[Depends(same_origin)])
def start(body: StartExecution, request: Request, response: Response, tasks: BackgroundTasks, db: Session = Depends(get_session)):
    owner, profile = owner_profile(request, db)
    graph = build_career_graph(profile, db)
    if body.role_id not in {n.entity_id for n in graph.nodes if n.type == "role"}: raise HTTPException(422)
    if body.node_id and body.node_id not in {n.id for n in graph.nodes if n.type!='profile'}: raise HTTPException(422)
    run = create(db, owner)
    _, workspace = private(request, db, lock=True)
    workspace.conversation = (workspace.conversation + [{
        "question": clean_text(body.question)[:1000], "execution_id": run.id,
        "role_id": body.role_id, "scenario": workspace.scenario,
        "node_id":body.node_id,
        "created_at": run.created_at.isoformat(),
    }])[-30:]
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    value = snapshot(db, run)
    tasks.add_task(execute, db.get_bind(), run.id, clean_text(body.question)[:1000], body.role_id, body.node_id)
    return value


@router.get("/{execution_id}")
def get(execution_id: str, request: Request, response: Response, db: Session = Depends(get_session)):
    owned(request, db, execution_id)
    recover(db)
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, owned(request, db, execution_id))


@router.post("/{execution_id}/cancel", dependencies=[Depends(same_origin)])
def cancel(execution_id: str, request: Request, response: Response, db: Session = Depends(get_session)):
    owned(request, db, execution_id)
    run = locked(db, execution_id)
    if run is None: raise HTTPException(404)
    if run.status not in TERMINAL:
        run.status = "cancelled"
        event(db, run, "cancelled")
        db.commit()
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, run)


@router.get("/{execution_id}/events")
def stream(execution_id: str, request: Request, db: Session = Depends(get_session)):
    owned(request, db, execution_id)
    try: cursor = max(0, int(request.headers.get("last-event-id", "0")))
    except ValueError: raise HTTPException(422)
    bind = db.get_bind()
    db.rollback()  # Do not retain a connection/transaction for the lifetime of the stream.
    async def events():
        nonlocal cursor
        def read():
            with Session(bind) as session:
                owned(request, session, execution_id)
                recover(session)
                return snapshot(session, owned(request, session, execution_id))
        while not await request.is_disconnected():
            try: value = await asyncio.to_thread(read)
            except HTTPException: return
            for item in value["events"]:
                if item["sequence"] > cursor:
                    cursor = item["sequence"]
                    yield f"id: {cursor}\nevent: activity\ndata: {json.dumps(item)}\n\n"
            if value["status"] in TERMINAL:
                yield "event: done\ndata: {}\n\n"
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
