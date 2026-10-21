"""Bounded aggregation over authoritative SQL records; no HTTP calls, writes or scoring changes."""
from datetime import datetime, timezone
from sqlalchemy import or_, select
from backend.app.career_graph_schemas import CareerEdge, CareerGraph, CareerNode
from backend.app.matching import LEVELS, METHOD, match_profile
from backend.app.models import ProfileSkill, Role, RoleSkill, SDG, SDGLink, SDGTarget, Skill, Source

MAX_ROLES = 5
MAX_GAPS_PER_ROLE = 3
MAX_SDG_LINKS = 6
MAX_OWNED_SKILLS = 60  # Same bound as the confirmed-profile API.


def build_career_graph(profile, db):
    """One typed node per canonical entity; retain per-role gaps on supported edges."""
    nodes, edges = {}, {}
    limitations = [
        "Skill fit is the existing heuristic, not a forecast, hiring probability or local vacancy claim.",
        "US O*NET requirements describe occupations; your preferred location does not establish local demand.",
        "Showing up to 5 roles, 3 priority gaps per role and 6 reviewed SDG links. Other relationships may exist.",
        "Gap fractions reflect self-reported proficiency relative to a particular role. SDG relevance is not measured impact or endorsement.",
        "Guide reads authoritative evidence; US sector forecasts and public research are separate from skill fit.",
    ]
    if profile is None:
        return CareerGraph(status="no_profile", profile_revision=None, generated_at=datetime.now(timezone.utc),
                           nodes=[], edges=[], sources=[], methodology=METHOD, limitations=limitations)
    pid = "profile:" + profile.id
    owned = list(db.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile.id).order_by(ProfileSkill.skill_id)))[:MAX_OWNED_SKILLS]
    levels = {s.skill_id: LEVELS[s.level] for s in owned}
    owned_by_id = {s.skill_id: s for s in owned}
    nodes[pid] = CareerNode(id=pid, type="profile", entity_id=profile.id, label="Demo profile" if profile.is_demo else "Your profile",
                            description="Your confirmed strengths and preferences", skill_count=len(owned), country=profile.country,
                            is_demo=profile.is_demo)
    matching = match_profile(profile, db)
    matches = matching["matches"][:MAX_ROLES]
    match_ids = [m["role_id"] for m in matches]
    roles = {r.id: r for r in db.scalars(select(Role).where(Role.id.in_(match_ids)))} if match_ids else {}
    # Only priority gaps from the unchanged matcher add absent skill nodes.
    priority = {m["role_id"]: {g["skill_id"] for g in m["gaps"][:MAX_GAPS_PER_ROLE]} for m in matches}
    skill_ids = set(levels) | {sid for ids in priority.values() for sid in ids}
    skills = list(db.scalars(select(Skill).where(Skill.id.in_(skill_ids)).order_by(Skill.id))) if skill_ids else []
    for skill in skills:
        record = owned_by_id.get(skill.id)
        sid = "skill:" + skill.id
        nodes[sid] = CareerNode(id=sid, type="owned_skill" if record else "required_skill", entity_id=skill.id,
            label=skill.canonical_name, description="Confirmed, self-reported skill" if record else "A displayed role's priority requirement",
            source_ids=[skill.source_id], level=record.level if record else None, years=record.years if record else None)
        if record:
            edge = CareerEdge(id=f"has_skill:{pid}:{sid}", type="has_skill", source=pid, target=sid,
                              supporting_id=f"{profile.id}:{skill.id}")
            edges[edge.id] = edge
    for match in matches:
        role = roles[match["role_id"]]
        rid = "role:" + role.id
        nodes[rid] = CareerNode(id=rid, type="role", entity_id=role.id, label=role.title, description=role.description,
            source_ids=sorted(set(match["source_ids"] + [role.source_id])), review_status=role.curation_status,
            score=match["score"], coverage=match["coverage"], explanation=match["explanation"], country=role.country)
    requirements = db.scalars(select(RoleSkill).where(RoleSkill.role_id.in_(match_ids), RoleSkill.skill_id.in_(skill_ids), RoleSkill.required_importance >= 3).order_by(RoleSkill.role_id, RoleSkill.skill_id)) if match_ids else []
    for requirement in requirements:
        rid, sid = "role:" + requirement.role_id, "skill:" + requirement.skill_id
        gap = round(1 - levels.get(requirement.skill_id, 0), 2)
        evidence = dict(source=rid, target=sid, source_ids=[requirement.source_id], importance=requirement.required_importance,
                        gap=gap, critical=requirement.required_importance >= 4, supporting_id=f"{requirement.role_id}:{requirement.skill_id}")
        edge = CareerEdge(id=f"requires_skill:{rid}:{sid}", type="requires_skill", **evidence)
        edges[edge.id] = edge
        if requirement.skill_id in priority[requirement.role_id]:
            edge = CareerEdge(id=f"missing_skill:{rid}:{sid}", type="missing_skill", **evidence)
            edges[edge.id] = edge
    # Do not infer or promote SDG links; only explicit human-reviewed, attributed records qualify.
    links = db.scalars(select(SDGLink).where(SDGLink.curation_status == "human_reviewed", SDGLink.reviewed_by.is_not(None),
        SDGLink.reviewed_at.is_not(None), or_(SDGLink.role_id.in_(match_ids), SDGLink.skill_id.in_(skill_ids))).order_by(SDGLink.id).limit(MAX_SDG_LINKS)).all() if skill_ids or match_ids else []
    target_ids = {link.target_id for link in links}
    targets = {t.id: t for t in db.scalars(select(SDGTarget).where(SDGTarget.id.in_(target_ids)))} if target_ids else {}
    goal_ids = {t.goal_id for t in targets.values()}
    goals = {g.id: g for g in db.scalars(select(SDG).where(SDG.id.in_(goal_ids)))} if goal_ids else {}
    for link in links:
        target = targets[link.target_id]
        goal = goals[target.goal_id]
        tid, gid = "sdg_target:" + target.id, "sdg:" + str(goal.id)
        nodes[tid] = CareerNode(id=tid, type="sdg_target", entity_id=target.id, label="Target " + target.id,
                               description=target.description, source_ids=[target.source_id], goal_id=goal.id)
        nodes[gid] = CareerNode(id=gid, type="sdg", entity_id=str(goal.id), label=f"Goal {goal.id}", description=goal.title,
                               source_ids=[goal.source_id], goal_id=goal.id)
        edge = CareerEdge(id="contributes_to_target:" + link.id, type="contributes_to_target",
                         source=("role:" + link.role_id) if link.role_id else ("skill:" + link.skill_id), target=tid,
                         source_ids=[link.source_id], review_status=link.curation_status, rationale=link.rationale, supporting_id=link.id)
        edges[edge.id] = edge
        edge = CareerEdge(id=f"target_belongs_to_goal:{target.id}", type="target_belongs_to_goal", source=tid, target=gid,
                         source_ids=[target.source_id], supporting_id=target.id)
        edges[edge.id] = edge
    used_sources = {sid for node in nodes.values() for sid in node.source_ids} | {sid for edge in edges.values() for sid in edge.source_ids}
    sources = db.scalars(select(Source).where(Source.id.in_(used_sources)).order_by(Source.id)).all() if used_sources else []
    return CareerGraph(status=matching["status"], profile_revision=profile.updated_at.isoformat(), generated_at=datetime.now(timezone.utc),
        nodes=sorted(nodes.values(), key=lambda n: n.id), edges=sorted(edges.values(), key=lambda e: e.id),
        sources=sources, methodology=METHOD, limitations=limitations)
