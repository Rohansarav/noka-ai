"""Deterministic, bounded skill-fit heuristic, independent of demand forecasts."""
from sqlalchemy import select
from backend.app.models import ProfileSkill, Role, RoleSkill, Skill

LEVELS = {"learning": 0.25, "working": 0.65, "strong": 1.0}
METHOD = "Skill coverage = sum(O*NET importance × self-rated level) / sum(importance), using role skills rated at least 3 of 5. Levels: learning 0.25, working 0.65, strong 1.0. Score = min(100, coverage × 100 + 5 for a selected role interest). Requires 3 confirmed skills. Years and location do not alter the score. This is a heuristic, not a probability or forecast. Critical gaps have importance ≥4."


def match_profile(profile, db):
    levels = {s.skill_id: LEVELS[s.level] for s in db.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile.id))}
    result = {"status": "insufficient_profile_information", "matches": [], "methodology": METHOD,
              "geography_note": "Skill requirements use US O*NET occupations. Your location is a preference; no Malaysian demand history or local job availability is inferred."}
    if not profile.confirmed or len(levels) < 3:
        return result
    rows = db.execute(select(RoleSkill, Skill).join(Skill).where(RoleSkill.required_importance >= 3)).all()
    grouped = {}
    for link, skill in rows:
        grouped.setdefault(link.role_id, []).append((link, skill))
    matches = []
    for role in db.scalars(select(Role)):
        requirements = grouped.get(role.id, [])
        total = sum(link.required_importance for link, _ in requirements)
        if not total:
            continue
        coverage = sum(link.required_importance * levels.get(skill.id, 0) for link, skill in requirements) / total
        transferable = [(link, skill) for link, skill in requirements if skill.category == "transferable"]
        transfer_total = sum(link.required_importance for link, _ in transferable)
        transfer_coverage = sum(link.required_importance * levels.get(skill.id, 0) for link, skill in transferable) / transfer_total if transfer_total else 0
        adjustment = 5 if role.id in profile.interests and coverage > 0 else 0
        gaps = [{"skill_id": skill.id, "name": skill.canonical_name, "importance": link.required_importance,
                 "gap": round(1 - levels.get(skill.id, 0), 2), "critical": link.required_importance >= 4}
                for link, skill in sorted(requirements, key=lambda pair: (-pair[0].required_importance, pair[1].canonical_name)) if levels.get(skill.id, 0) < 1]
        matches.append({"role_id": role.id, "title": role.title, "score": round(min(100, coverage * 100 + adjustment), 1),
            "coverage": round(coverage * 100, 1), "transferable_coverage": round(transfer_coverage * 100, 1),
            "interest_adjustment": adjustment, "gaps": gaps,
            "explanation": f"Your self-rated skills cover {coverage:.0%} of weighted requirements across {len(requirements)} important skills. Selected-role interest adds {adjustment} points. Transferable skills are included once in coverage, with a separate breakdown. Years are not scored because role experience thresholds are unavailable.",
            "source_ids": sorted({link.source_id for link, _ in requirements})})
    result.update(status="ready" if matches else "insufficient_profile_information", matches=sorted(matches, key=lambda m: (-m["score"], m["title"], m["role_id"]))[:5])
    return result
