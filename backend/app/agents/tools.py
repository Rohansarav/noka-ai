"""Direct SQL/service adapters. Neither the model nor caller can select a profile."""
from sqlalchemy import select, or_
from backend.app.models import ProfileSkill, Skill, Role, RoleSkill, RoleTechnology, SDGLink, Source
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
        from backend.app.models import FutureWorkspace
        workspace = db.get(FutureWorkspace, profile.id)
        return {"confirmed": profile.confirmed, "country": profile.country, "interests": profile.interests,
                'analysis_context': profile.analysis_context or {},
                "future_context": {"scenario": workspace.scenario, "selected_role": workspace.role_id,
                                   "weekly_hours": workspace.weekly_hours, "saved_progress": workspace.progress} if workspace else None}
    if name == "get_confirmed_skills":
        return [{"skill_id": s.id, "name": s.canonical_name, "level": p.level} for p, s in db.execute(select(ProfileSkill, Skill).join(Skill).where(ProfileSkill.profile_id == profile.id))]
    if name == "get_future_context":
        from backend.app.future import snapshot
        from backend.app.models import FutureWorkspace
        workspace=db.get(FutureWorkspace,profile.id)
        if not workspace: return {"status":"Choose a future direction first."}
        value=snapshot(profile,workspace,db)
        value.pop("conversation",None)
        return value
    if name == "get_forecast_context":
        from backend.app.future import forecasts
        report=forecasts()
        role=db.get(Role,role_id)
        return {"status":report["status"],"sector":role.sector,"market":"US",
                "limitation":"Sector proxy, not a Malaysian role forecast.",
                "forecasts":[{k:v for k,v in r.items() if k!="backtests"} for r in report.get("sectors",[]) if r["sector"]==role.sector]}
    if name == "get_scout_findings":
        from backend.app.models import IntelligenceRecord
        findings=[r.payload for r in db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.kind.in_(["finding","context"])))]
        return [{"title":f["title"],"url":f["url"],"market":f["market"],"review_status":f["review_status"],
                 "retrieved_at":f["retrieved_at"]} for f in findings if role_id in f.get("role_ids",[])][:5]
    matches = match_profile(profile, db, limit=None)
    if name == "get_ranked_matches":
        return {**matches, 'matches':[m for m in matches['matches'] if m['role_id'] in allowed_roles]}
    if name == "get_skill_gaps":
        return next(m["gaps"] for m in matches["matches"] if m["role_id"] == role_id)
    if name == "get_role_requirements":
        rated=[{"skill_id": s.id, "name": s.canonical_name, "importance": r.required_importance, "source_id": r.source_id,'evidence_kind':'rated_skill'}
                for r, s in db.execute(select(RoleSkill, Skill).join(Skill).where(RoleSkill.role_id == role_id))]
        software=[{'skill_id':s.id,'name':s.canonical_name,'importance':None,'source_id':r.source_id,'evidence_kind':'software_association'}
                  for r,s in db.execute(select(RoleTechnology,Skill).join(Skill,RoleTechnology.skill_id==Skill.id).where(RoleTechnology.role_id==role_id).order_by(RoleTechnology.in_demand.desc(),RoleTechnology.hot_technology.desc(),Skill.canonical_name).limit(64))]
        return rated+software
    if name == "get_role_evidence":
        role = db.get(Role, role_id)
        source = db.get(Source, role.source_id)
        return {"role_id": role.id, "sector": role.sector, "evidence_status": role.evidence_status,
                "limitation": "Sector proxy only; no individual-role forecast or local vacancies.",
                "source_id": source.id, "url": source.canonical_url, "publisher": source.publisher}
    skill_ids = select(RoleSkill.skill_id).where(RoleSkill.role_id == role_id,RoleSkill.required_importance>=2)
    links = db.scalars(select(SDGLink).where(SDGLink.curation_status == "human_reviewed", SDGLink.reviewed_by.is_not(None), SDGLink.reviewed_at.is_not(None), or_(SDGLink.role_id == role_id, SDGLink.skill_id.in_(skill_ids)))).all()
    return [{"target_id": l.target_id, "role_id": l.role_id, "skill_id": l.skill_id, "rationale": l.rationale, "source_id": l.source_id,
             "limitation": "Explicit entity link only; a skill link does not imply a role-to-SDG link or measured impact."} for l in links]
