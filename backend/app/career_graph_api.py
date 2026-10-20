"""Session-derived universe endpoint: read-only and never accepts a caller-selected profile ID."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.career_graph import build_career_graph
from backend.app.career_graph_schemas import CareerGraph
from backend.app.evidence_api import get_session
from backend.app.models import Profile
from backend.app.profile_security import active_session, owned_profile

router = APIRouter(prefix="/api/profiles/current", tags=["Private career universe"])


@router.get("/career-graph", response_model=CareerGraph)
def career_graph(request: Request, response: Response, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    owner = active_session(request, db)
    profile = db.scalar(select(Profile).where(Profile.session_hash == owner.token_hash)) if owner else None
    return build_career_graph(owned_profile(profile.id, request, db) if profile else None, db)
