"""Transactional event journal, ownership and deadline recovery; not a durable job queue."""
from datetime import datetime, timezone, timedelta
import secrets
from fastapi import HTTPException
from sqlalchemy import select, update, text
from backend.app.models import AgentExecution, AgentEvent, PrivateSession, Profile
from backend.app.profile_security import active_session
from backend.app.config import get_settings
from backend.app.agents.contracts import EventPayload

TERMINAL = {"completed", "failed", "cancelled"}
MESSAGES = {"queued": "Matchmaker request accepted.", "running": "Matchmaker worker started.",
            "tool_completed": "Read-only tool completed.", "completed": "Evidence-backed exploration ready.",
            "failed": "AI exploration unavailable. Your deterministic Universe remains available.", "cancelled": "Exploration cancelled."}


def now(): return datetime.now(timezone.utc)


def locked(db, execution_id) -> AgentExecution | None:
    # An UPDATE acquires a write lock on both PostgreSQL and SQLite before event allocation.
    db.execute(update(AgentExecution).where(AgentExecution.id == execution_id).values(event_sequence=AgentExecution.event_sequence))
    return db.scalar(select(AgentExecution).where(AgentExecution.id == execution_id).execution_options(populate_existing=True))


def event(db, run, kind, payload=None):
    """Allocate a unique monotonically increasing sequence in the caller's transaction."""
    run.event_sequence += 1
    run.updated_at = now()
    db.add(AgentEvent(execution_id=run.id, sequence=run.event_sequence, created_at=run.updated_at,
                      agent=run.agent, type=kind, status=run.status, message=MESSAGES[kind], payload=EventPayload.model_validate(payload or {}).model_dump(exclude_none=True)))


def recover(db):
    """Expired leases fail on access. A restarted process never replays private questions."""
    ids = list(db.scalars(select(AgentExecution.id).where(AgentExecution.status.in_(["queued", "running"]), AgentExecution.deadline <= now())))
    for execution_id in ids:
        run = locked(db, execution_id)
        if run and run.status not in TERMINAL and run.deadline <= now():
            run.status, run.error_code = "failed", "deadline_or_interrupted"
            event(db, run, "failed")
    db.commit()


def owner_profile(request, db) -> tuple[PrivateSession, Profile]:
    owner = active_session(request, db)
    if owner is None: raise HTTPException(404)
    profile = db.scalar(select(Profile).where(Profile.session_hash == owner.token_hash))
    if not profile: raise HTTPException(404)
    return owner, profile


def owned(request, db, execution_id) -> AgentExecution:
    owner, _ = owner_profile(request, db)
    run = db.get(AgentExecution, execution_id)
    if not run or run.session_hash != owner.token_hash: raise HTTPException(404)
    return run


def create(db, owner):
    settings = get_settings()
    recover(db)
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(7395135)"))
    db.execute(update(PrivateSession).where(PrivateSession.token_hash == owner.token_hash).values(expires_at=PrivateSession.expires_at))
    recent = list(db.scalars(select(AgentExecution).where(AgentExecution.session_hash == owner.token_hash, AgentExecution.created_at >= now() - timedelta(days=1))))
    global_active = len(list(db.scalars(select(AgentExecution.id).where(AgentExecution.status.in_(["queued", "running"])))))
    if global_active >= settings.agent_global_concurrent or len(recent) >= settings.agent_daily_quota or sum(r.status not in TERMINAL for r in recent) >= settings.agent_max_concurrent:
        db.rollback()
        raise HTTPException(429)
    run = AgentExecution(id=secrets.token_urlsafe(24), session_hash=owner.token_hash, agent="matchmaker", status="queued",
                         created_at=now(), updated_at=now(), deadline=now()+timedelta(seconds=settings.agent_timeout_seconds),
                         model=settings.openai_guide_model, tool_count=0, token_usage=0, event_sequence=0)
    db.add(run)
    db.flush()
    event(db, run, "queued")
    db.commit()
    return run


def snapshot(db, run):
    return {"id": run.id, "agent": run.agent, "status": run.status, "created_at": run.created_at.isoformat(),
            "error_code": run.error_code, "tool_count": run.tool_count, "token_usage": run.token_usage, "result": run.result,
            "events": [{"sequence": e.sequence, "agent": e.agent, "type": e.type, "status": e.status, "at": e.created_at.isoformat(),
                        "message": e.message, "payload": e.payload} for e in db.scalars(select(AgentEvent).where(AgentEvent.execution_id == run.id).order_by(AgentEvent.sequence))]}
