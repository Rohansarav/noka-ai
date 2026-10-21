"""Owned profiles and bounded structured onboarding drafts; raw resumes are discarded."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from backend.app.evidence_api import get_session
from backend.app.models import FutureWorkspace, PrivateSession, Profile, ProfileSkill, Role, Skill
from backend.app.profile_schemas import AnalysisInput, CreateProfile, CurrentProfile, ExtractionResponse, MatchesResponse, ProfileView, SaveSkills, OnboardingDraft
from backend.app.profile_security import COOKIE, active_session, owned_profile, same_origin, token_hash
from backend.app.skill_extraction import clean_text, extract, parse_upload
from backend.app.matching import match_profile

router = APIRouter(prefix="/api/profiles", tags=["Private profiles"])


def view(profile, db):
    return ProfileView(id=profile.id, country=profile.country, interests=profile.interests, is_demo=profile.is_demo,
        confirmed=profile.confirmed, updated_at=profile.updated_at.isoformat(), onboarding=profile.onboarding,
        skills=[{"skill_id": s.skill_id, "level": s.level, "years": s.years} for s in db.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile.id).order_by(ProfileSkill.skill_id))])


@router.get("/current", response_model=CurrentProfile)
def current(request: Request, response: Response, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    owner = active_session(request, db)
    profile = db.scalar(select(Profile).where(Profile.session_hash == owner.token_hash)) if owner else None
    return {"profile": view(profile, db) if profile else None}


@router.post("", response_model=ProfileView, dependencies=[Depends(same_origin)])
def create(body: CreateProfile, request: Request, response: Response, db: Session = Depends(get_session)):
    owner = active_session(request, db)
    if not owner:
        token = secrets.token_urlsafe(32)
        owner = PrivateSession(token_hash=token_hash(token), expires_at=datetime.now(timezone.utc) + timedelta(days=30))
        db.add(owner)
        db.flush()
        response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme == "https" or request.url.hostname not in {"localhost", "127.0.0.1", "testserver"}, samesite="strict", max_age=2592000, path="/")
    profile = db.scalar(select(Profile).where(Profile.session_hash == owner.token_hash))
    if not profile:
        profile = Profile(id=secrets.token_urlsafe(24), session_hash=owner.token_hash, is_demo=body.is_demo, updated_at=datetime.now(timezone.utc))
        db.add(profile)
        db.commit()
    response.headers["Cache-Control"] = "no-store"
    return view(profile, db)


@router.get("/{profile_id}", response_model=ProfileView)
def get_profile(profile_id: str, request: Request, response: Response, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return view(owned_profile(profile_id, request, db), db)


@router.post("/{profile_id}/analysis", response_model=ExtractionResponse, dependencies=[Depends(same_origin)])
@router.post("/{profile_id}/resume", response_model=ExtractionResponse, dependencies=[Depends(same_origin)])
def resume(profile_id: str, request: Request, response: Response,
           file: Annotated[UploadFile | None, File()] = None,
           text: Annotated[str, Form(max_length=20000)] = "",
           use_ai: Annotated[bool, Form()] = False, db: Session = Depends(get_session)):
    owned_profile(profile_id, request, db)
    response.headers["Cache-Control"] = "no-store"
    if file and text or not file and not text.strip():
        raise HTTPException(422)
    if file:
        try:
            data = file.file.read(5 * 1024 * 1024 + 1)
            text = parse_upload(data, file.filename, file.content_type)
        except ValueError as exc:
            return JSONResponse(status_code=413 if str(exc) == "size" else 422, content={"error": {
                "code": "upload_too_large" if str(exc) == "size" else "unreadable_document",
                "message": "Choose a PDF or DOCX up to 5 MB." if str(exc) == "size" else "This document could not be read. Use an unencrypted text PDF or DOCX, or enter your experience manually."}})
        finally:
            file.file.close()
    was_truncated = len(text) > 20000
    if request.url.path.endswith("/analysis"):
        try:
            standard = AnalysisInput(text=clean_text(text))
        except ValidationError:
            return JSONResponse(status_code=422, content={"error": {"code": "insufficient_experience", "message":
                "No readable experience was found. Scanned PDFs need OCR; enter your experience manually instead." if file else
                "Describe your experience in at least 20 characters, including tasks, projects or skills."}})
        text = standard.text
    catalogue = list(db.scalars(select(Skill).order_by(Skill.id)))
    if not catalogue:
        return JSONResponse(status_code=503, content={"error": {"code": "catalogue_unavailable", "message": "The skill catalogue is unavailable. Your input has not been saved; retry when it is available."}})
    result = extract(text, catalogue, use_ai)
    result.truncated = result.truncated or was_truncated
    return result


@router.put("/{profile_id}/onboarding", response_model=ProfileView, dependencies=[Depends(same_origin)])
def save_draft(profile_id: str, body: OnboardingDraft, request: Request, response: Response, db: Session = Depends(get_session)):
    """Persist only bounded structured fields; resume text and suggestions never enter drafts."""
    profile = owned_profile(profile_id, request, db)
    ids = [s.skill_id for s in body.skills]
    if len(ids) != len(set(ids)) or set(ids) - set(db.scalars(select(Skill.id))) or set(body.interests) - set(db.scalars(select(Role.id))):
        raise HTTPException(422)
    profile.onboarding = body.model_dump()
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return view(profile, db)


@router.put("/{profile_id}/skills", response_model=ProfileView, dependencies=[Depends(same_origin)])
def save(profile_id: str, body: SaveSkills, request: Request, response: Response, db: Session = Depends(get_session)):
    profile = owned_profile(profile_id, request, db)
    ids = [s.skill_id for s in body.skills]
    if len(ids) != len(set(ids)) or set(ids) - set(db.scalars(select(Skill.id))) or set(body.interests) - set(db.scalars(select(Role.id))):
        raise HTTPException(422)
    if body.onboarding and (len(ids) < 3 or not body.onboarding.current_field.strip()):
        raise HTTPException(422)
    db.execute(delete(ProfileSkill).where(ProfileSkill.profile_id == profile_id))
    for skill in body.skills:
        db.add(ProfileSkill(profile_id=profile_id, **skill.model_dump()))
    profile.country, profile.interests, profile.confirmed = body.country, sorted(set(body.interests)), True
    if body.onboarding:
        profile.onboarding = {**body.onboarding.model_dump(), "skills": [s.model_dump() for s in body.skills], "completed": True}
        workspace = db.get(FutureWorkspace, profile_id)
        if not workspace:
            workspace = FutureWorkspace(profile_id=profile_id, scenario="collaboration", progress={}, conversation=[], updated_at=datetime.now(timezone.utc))
            db.add(workspace)
        workspace.weekly_hours = body.onboarding.weekly_hours
        db.flush()
        from backend.app.future import ranked
        directions = ranked(profile, db, workspace.scenario)
        if workspace.role_id not in {m["role_id"] for m in directions}:
            workspace.role_id = directions[0]["role_id"] if directions else None
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return view(profile, db)


@router.get("/{profile_id}/matches", response_model=MatchesResponse)
def matches(profile_id: str, request: Request, response: Response, db: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return match_profile(owned_profile(profile_id, request, db), db)


@router.delete("/{profile_id}", status_code=204, dependencies=[Depends(same_origin)])
def remove(profile_id: str, request: Request, response: Response, db: Session = Depends(get_session)):
    profile = owned_profile(profile_id, request, db)
    db.execute(delete(ProfileSkill).where(ProfileSkill.profile_id == profile_id))
    owner_hash = profile.session_hash
    db.delete(profile)
    db.flush()
    db.execute(delete(PrivateSession).where(PrivateSession.token_hash == owner_hash))
    db.commit()
    response.delete_cookie(COOKIE, path="/")
