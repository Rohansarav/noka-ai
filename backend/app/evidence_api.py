from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.database import engine
from backend.app.models import DemandObservation, IngestionRun, Role, RoleSkill, SDG, SDGLink, SDGTarget, Skill, Source, StructuralDirection
from backend.app.schemas import HistoryResponse, RoleDetail, RolesResponse, SDGsResponse, SkillsResponse, SummaryResponse

router = APIRouter(prefix="/api", tags=["Public evidence"])


def get_session():
    with Session(engine) as session:
        yield session


def link_records(session):
    """Resolve graph labels in three queries, rather than per goal/target."""
    titles = dict(session.execute(select(Role.id, Role.title)).all())
    names = dict(session.execute(select(Skill.id, Skill.canonical_name)).all())
    return [{"target_id": r.target_id, "role_id": r.role_id, "skill_id": r.skill_id, "entity_name": titles.get(r.role_id) or names.get(r.skill_id) or "Unknown", "rationale": r.rationale, "source_id": r.source_id, "curation_status": r.curation_status, "reviewed_by": r.reviewed_by, "reviewed_at": r.reviewed_at} for r in session.scalars(select(SDGLink).order_by(SDGLink.id))]


@router.get("/roles", response_model=RolesResponse)
def roles(session: Session = Depends(get_session)):
    return {"roles": session.scalars(select(Role).order_by(Role.title)).all()}


@router.get("/roles/{role_id}", response_model=RoleDetail)
def role_detail(role_id: str, session: Session = Depends(get_session)):
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(404)
    result = {c.name: getattr(role, c.name) for c in Role.__table__.columns}
    result.update(source=session.get(Source, role.source_id),
                  skills=[{"skill": skill, "required_importance": link.required_importance, "source_id": link.source_id} for link, skill in session.execute(select(RoleSkill, Skill).join(Skill, RoleSkill.skill_id == Skill.id).where(RoleSkill.role_id == role_id).order_by(RoleSkill.required_importance.desc(), Skill.canonical_name))],
                  sdg_links=[link for link in link_records(session) if link["role_id"] == role_id])
    return result


@router.get("/skills", response_model=SkillsResponse)
def skills(session: Session = Depends(get_session)):
    return {"skills": session.scalars(select(Skill).order_by(Skill.canonical_name)).all()}


@router.get("/datasets/summary", response_model=SummaryResponse)
def datasets_summary(session: Session = Depends(get_session)):
    counts = {model.__tablename__: session.scalar(select(func.count()).select_from(model)) for model in [Role, Skill, RoleSkill, DemandObservation, SDG, SDGTarget, SDGLink]}
    start, end = session.execute(select(func.min(DemandObservation.date), func.max(DemandObservation.date))).one()
    sector_rows = session.execute(select(DemandObservation.country, DemandObservation.sector, func.count(), func.min(DemandObservation.date), func.max(DemandObservation.date)).group_by(DemandObservation.country, DemandObservation.sector).order_by(DemandObservation.sector)).all()
    runs = session.scalars(select(IngestionRun).order_by(IngestionRun.completed_at.desc())).all()
    successful, seen = [], set()
    for run in runs:
        if run.status == "success" and run.dataset not in seen:
            successful.append(run)
            seen.add(run.dataset)
    return {"database": session.bind.dialect.name, "counts": counts, "countries": list(session.scalars(select(DemandObservation.country).distinct()).all()), "start_date": start, "end_date": end,
            "sectors": [{"country": r[0], "sector": r[1], "observation_count": r[2], "start_date": r[3], "end_date": r[4]} for r in sector_rows],
            "sources": session.scalars(select(Source).order_by(Source.dataset, Source.retrieved_at.desc())).all(), "last_successful_imports": successful, "last_attempt": runs[0] if runs else None,
            "structural_directions": session.scalars(select(StructuralDirection).order_by(StructuralDirection.id)).all(),
            "limitations": ["US occupational-sector indices are not Malaysian or individual-role/skill time series.", "Index values are relative to 2020-02-01=100, not posting counts, salaries or probabilities.", "Daily indices use seven-day trailing averages and seasonal adjustment; source histories can be revised.", "No trained forecast exists. Sector crosswalks and SDG relevance are editorial judgements, not statistical forecasts or measured impact.", "Retrieval time, import time and source publication date are different; unknown publication dates remain null."]}


@router.get("/demand/history", response_model=HistoryResponse)
def demand_history(sector: str = Query(min_length=1, max_length=120), start: date | None = None, end: date | None = None, session: Session = Depends(get_session)):
    if start and end and start > end:
        raise HTTPException(422)
    query = select(DemandObservation).where(DemandObservation.country == "US", DemandObservation.sector == sector, DemandObservation.adjusted_flag.is_(True)).order_by(DemandObservation.date)
    if start:
        query = query.where(DemandObservation.date >= start)
    if end:
        query = query.where(DemandObservation.date <= end)
    points = session.scalars(query).all()
    if not points and not session.scalar(select(DemandObservation.sector).where(DemandObservation.sector == sector).limit(1)):
        raise HTTPException(404)
    source_ids = {p.source_id for p in points}
    return {"sector": sector, "points": points, "sources": session.scalars(select(Source).where(Source.id.in_(source_ids))).all() if source_ids else []}


@router.get("/sdgs", response_model=SDGsResponse)
def sdgs(session: Session = Depends(get_session)):
    links = link_records(session)
    targets = session.scalars(select(SDGTarget).order_by(SDGTarget.id)).all()
    goals = []
    for g in session.scalars(select(SDG).order_by(SDG.id)):
        goals.append({"id": g.id, "title": g.title, "description": g.description, "source_id": g.source_id, "official_url": f"https://sdgs.un.org/goals/goal{g.id}", "targets": [{"id": t.id, "goal_id": t.goal_id, "description": t.description, "source_id": t.source_id, "links": [link for link in links if link["target_id"] == t.id]} for t in targets if t.goal_id == g.id]})
    return {"goals": goals, "sources": session.scalars(select(Source).where(Source.dataset == "un-sdgs")).all()}
