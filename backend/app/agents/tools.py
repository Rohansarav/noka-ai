"""Direct SQL/service adapters. Neither the model nor caller can select a profile."""
from sqlalchemy import select, or_
from backend.app.models import ProfileSkill, Skill, Role, RoleSkill, SDGLink, Source
from backend.app.matching import match_profile
from backend.app.agents.registry import TOOLS


def invoke(name, arguments, profile, db, allowed_roles):
    if name not in TOOLS:
        raise ValueError("unauthorized_tool")
    args = TOOLS[name].model_validate_json(arguments)
    role_id = getattr(args, "role_id", None)
    if role_id is not None and role_id not in allowed_roles:
        raise ValueError("invalid_reference")
    if name == "get_current_profile":
        return {"confirmed": profile.confirmed, "country": profile.country, "interests": profile.interests}
    if name == "get_confirmed_skills":
        return [{"skill_id": s.id, "name": s.canonical_name, "level": p.level} for p, s in db.execute(select(ProfileSkill, Skill).join(Skill).where(ProfileSkill.profile_id == profile.id))]
    matches = match_profile(profile, db)
    if name == "get_ranked_matches":
        return matches
    if name == "get_skill_gaps":
        return next(m["gaps"] for m in matches["matches"] if m["role_id"] == role_id)
    if name == "get_role_requirements":
        return [{"skill_id": s.id, "name": s.canonical_name, "importance": r.required_importance, "source_id": r.source_id}
                for r, s in db.execute(select(RoleSkill, Skill).join(Skill).where(RoleSkill.role_id == role_id))]
    if name == "get_role_evidence":
        role = db.get(Role, role_id)
        source = db.get(Source, role.source_id)
        return {"role_id": role.id, "sector": role.sector, "evidence_status": role.evidence_status,
                "limitation": "Sector proxy only; no individual-role forecast or local vacancies.",
                "source_id": source.id, "url": source.canonical_url, "publisher": source.publisher}
    skill_ids = select(RoleSkill.skill_id).where(RoleSkill.role_id == role_id)
    links = db.scalars(select(SDGLink).where(SDGLink.curation_status == "human_reviewed", SDGLink.reviewed_by.is_not(None), SDGLink.reviewed_at.is_not(None), or_(SDGLink.role_id == role_id, SDGLink.skill_id.in_(skill_ids)))).all()
    return [{"target_id": l.target_id, "role_id": l.role_id, "skill_id": l.skill_id, "rationale": l.rationale, "source_id": l.source_id,
             "limitation": "Explicit entity link only; a skill link does not imply a role-to-SDG link or measured impact."} for l in links]
