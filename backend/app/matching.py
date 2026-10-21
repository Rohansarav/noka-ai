"""Explainable readiness, explicit aspirations and source-bound development priorities."""
import re
from sqlalchemy import select
from backend.app.models import ProfileSkill
from backend.app.occupation_catalogue import occupation_evidence

LEVELS = {'learning': .25, 'working': .65, 'strong': 1.0}
METHOD = ('Readiness = sum(O*NET importance × self-rated level) / sum(importance) × 100, using importance ≥3/5. '
          'Levels: learning .25, working .65, strong 1. Interests do not increase readiness. '
          'All supported occupations are ranked before display; up to five explicit targets are retained alongside five discoveries. '
          'Context alignment is a separate lexical relevance signal, not skill evidence or a probability. '
          'Development priority = importance × remaining proficiency gap; scenario emphasis breaks ties. '
          'This is not a probability or forecast. US occupational requirements do not establish local vacancies. Years are not scored.')
STOP = set('i my me a an and or the to of in on for with from as at is be am have has want work working build building into career role job experience study studying project projects system systems using used'.split())


def confirmed_context(profile):
    # Never read editable drafts: analysis changes only after explicit profile confirmation.
    return getattr(profile, 'analysis_context', None) or {}


def context_alignment(profile, role):
    reasons, scores = [], []
    context = confirmed_context(profile)
    evidence = set(re.findall(r'[a-z]{3,}', (role.title+' '+role.description).lower())) - STOP
    for key, label in [('goal','goal'), ('current_field','background'), ('projects','project context')]:
        tokens = set(re.findall(r'[a-z]{3,}', context.get(key, '').lower())) - STOP
        overlap = sorted(tokens & evidence)
        if overlap:
            scores.append(len(overlap)/max(1,len(tokens)))
            reasons.append(f"{label}: shared terms {', '.join(overlap[:5])}. Lexical relevance, not verified proficiency.")
    return round(max(scores, default=0), 3), reasons


def prioritize_gaps(gaps, scenario_skills=()):
    """One rule for graph and pathway; substantial deficits outrank minor deficits."""
    return sorted(gaps, key=lambda g: (-g['priority'], g['name'] not in scenario_skills, -g['importance'], g['name'], g['skill_id']))


def select_directions(matches, limit=5):
    targets = [m for m in matches if m['is_target']]
    discoveries = [m for m in matches if not m['is_target']][:limit]
    return targets + discoveries


def match_profile(profile, db, limit=5):
    levels = {s.skill_id: LEVELS[s.level] for s in db.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile.id))}
    result = {'status':'insufficient_profile_information', 'matches':[], 'methodology':METHOD,
              'geography_note':'Skill requirements use US O*NET occupations. Market is a preference, not evidence of local demand.'}
    if not profile.confirmed or len(levels) < 3:
        return result
    grouped = {}
    roles, requirements = occupation_evidence(db)
    for link, skill in requirements:
        if link.required_importance >= 3:
            grouped.setdefault(link.role_id, []).append((link,skill))
    matches = []
    for role in roles:
        requirements = grouped.get(role.id, [])
        total = sum(link.required_importance for link,_ in requirements)
        if not total:
            continue
        coverage = sum(link.required_importance*levels.get(skill.id,0) for link,skill in requirements)/total
        transferable = [(link,skill) for link,skill in requirements if skill.category == 'transferable']
        transfer_total = sum(link.required_importance for link,_ in transferable)
        transfer = sum(link.required_importance*levels.get(skill.id,0) for link,skill in transferable)/transfer_total if transfer_total else 0
        alignment, reasons = context_alignment(profile,role)
        target = role.id in profile.interests
        gaps = prioritize_gaps([{'skill_id':skill.id,'name':skill.canonical_name,'importance':link.required_importance,
                     'gap':round(1-levels.get(skill.id,0),2), 'critical':link.required_importance >= 4,
                     'priority':round(link.required_importance*(1-levels.get(skill.id,0)),4),
                     'development':'developing' if skill.id in levels else 'missing'}
                    for link,skill in requirements if levels.get(skill.id,0) < 1])
        matches.append({'role_id':role.id,'title':role.title,'score':round(coverage*100,1),'coverage':round(coverage*100,1),
                        'transferable_coverage':round(transfer*100,1),'interest_adjustment':0,'gaps':gaps,
                        'is_target':target,'context_alignment':alignment,'context_reasons':reasons,
                        'selection_reason':'Your confirmed target; retained regardless of readiness.' if target else 'Discovered from all supported occupations using readiness and separate context relevance.',
                        'explanation':f"Weighted readiness {coverage:.0%} across {len(requirements)} important requirements. Interest does not increase readiness. Self-ratings are not a verified skills assessment; years are not scored.",
                        'source_ids':sorted({link.source_id for link,_ in requirements})})
    matches.sort(key=lambda m:(-(m['score']+5*m['context_alignment']),-m['score'],m['title'],m['role_id']))
    result.update(status='ready' if matches else 'insufficient_profile_information',matches=matches if limit is None else select_directions(matches,limit))
    return result
