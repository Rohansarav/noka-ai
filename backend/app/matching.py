"""Explainable readiness, explicit aspirations and source-bound development priorities."""
import re
from sqlalchemy import select
from backend.app.models import ProfileSkill
from backend.app.occupation_catalogue import occupation_evidence, skill_evidence

LEVELS = {'learning': .25, 'working': .65, 'strong': 1.0}
METHOD = ('Documented coverage = sum(O*NET importance × self-rated level) / sum(importance) × 100, using importance ≥3/5. '
          'Levels: learning .25, working .65, strong 1. Interests do not increase readiness. '
          'Software alignment counts distinct published occupation associations separately; tools add no broad readiness credit. Discovery requires multiple occupational connections and ranks relevance separately from coverage. Sparse requirement records cannot qualify through coverage alone. All supported occupations are ranked before display; up to five explicit targets are retained alongside five discoveries. '
          'Context alignment is a separate lexical relevance signal, not skill evidence or a probability. '
          'A missing self-rating is unknown, not proof of inability. The score is documented weighted coverage; evidence completeness and proficiency among recorded requirements are reported separately. '
          'Development priority = importance × remaining proficiency gap × 1.25 for scenario focus skills, otherwise × 1. This explicit planning assumption changes learning order, never factual coverage. '
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
    """Shared planning rule; scenario weighting never changes the evidence or fit score."""
    return sorted(gaps, key=lambda g: (-g['priority']*(1.25 if g['name'] in scenario_skills else 1), -g['importance'], g['name'], g['skill_id']))


def select_directions(matches, limit=5):
    targets = [m for m in matches if m['is_target']]
    discoveries = sorted((m for m in matches if not m['is_target'] and m.get('discovery_relevance', 0) > 0),
                         key=lambda m: (-m['discovery_relevance'], -m.get('context_alignment', 0), m['title'], m['role_id']))[:limit]
    return targets + discoveries


def discovery_relevance(role, requirements, targets, levels, technical):
    """Gate discovery on multiple occupational connections, never coverage percentages.

    O*NET detailed occupation families plus shared requirements support adjacency.
    Software or non-transferable skills support discovery without a chosen target.
    These conservative rules are planning heuristics, not validated suitability scores.
    """
    ids = {skill.id for _, skill in requirements}
    reasons, strength = [], 0
    if len(ids) < 3:
        return 0, []
    for target, target_ids in targets:
        shared = ids & target_ids
        family = role.occupation_code[:4] == target.occupation_code[:4]
        if family and len(shared) >= 3:
            strength = max(strength, 3 + len(shared) / max(len(ids | target_ids), 1))
            reasons.append(f"Related to your {target.title} target: same O*NET occupation family and {len(shared)} shared important requirements.")
    # Import categories call basic skills "essential" and technical skills
    # "transferable". Use O*NET technical/system element IDs, not those categories.
    specific = [s.canonical_name for _, s in requirements if s.id in levels and
                (s.id.startswith('2.B.3.') or s.id in {'2.B.4.g', '2.B.4.h'})]
    if len(specific) >= 2 or (specific and len(ids & levels.keys()) >= 3):
        strength = max(strength, 2 + min(len(specific), 5) / 10)
        reasons.append('Confirmed occupational skills: ' + ', '.join(sorted(specific)[:4]) + '.')
    if technical['matched_count'] >= 2:
        strength = max(strength, 2 + min(technical['matched_count'], 5) / 10)
        reasons.append('Published software connections: ' + ', '.join(s['name'] for s in technical['matched'][:4]) + '.')
    return round(strength, 3), reasons


def match_profile(profile, db, limit=5):
    levels = {s.skill_id: LEVELS[s.level] for s in db.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile.id))}
    result = {'status':'insufficient_profile_information', 'matches':[], 'methodology':METHOD,
              'geography_note':'Skill requirements use US O*NET occupations. Market is a preference, not evidence of local demand.'}
    context=confirmed_context(profile)
    if not profile.confirmed or len(levels)+len(context.get('custom_skills',[])) < 3:
        return result
    concepts, software_links=skill_evidence(db)
    software_by_role={}
    for link in software_links:software_by_role.setdefault(link.role_id,[]).append(link)
    grouped = {}
    roles, requirements = occupation_evidence(db)
    for link, skill in requirements:
        if link.required_importance >= 3:
            grouped.setdefault(link.role_id, []).append((link,skill))
    matches = []
    targets = [(r, {s.id for _, s in grouped.get(r.id, [])}) for r in roles if r.id in profile.interests]
    for role in roles:
        requirements = grouped.get(role.id, [])
        total = sum(link.required_importance for link,_ in requirements)
        if not total:
            continue
        coverage = sum(link.required_importance*levels.get(skill.id,0) for link,skill in requirements)/total
        recorded = [(link, skill) for link, skill in requirements if skill.id in levels]
        recorded_weight = sum(link.required_importance for link, _ in recorded)
        assessment = {'required_count':len(requirements),'recorded_count':len(recorded),
                      'unrecorded_count':len(requirements)-len(recorded),
                      'evidence_completeness':round(100*recorded_weight/total,1),
                      'assessed_proficiency':round(100*coverage*total/recorded_weight,1) if recorded_weight else None,
                      'status':'complete' if len(recorded)==len(requirements) else 'partial' if recorded else 'unassessed',
                      'method':'Documented coverage = weighted evidence completeness × self-rated proficiency among recorded requirements / 100. Unrecorded requirements receive no credit, but are unknown rather than demonstrated weaknesses. Software is separate.'}
        transferable = [(link,skill) for link,skill in requirements if skill.category == 'transferable']
        transfer_total = sum(link.required_importance for link,_ in transferable)
        transfer = sum(link.required_importance*levels.get(skill.id,0) for link,skill in transferable)/transfer_total if transfer_total else 0
        alignment, reasons = context_alignment(profile,role)
        target = role.id in profile.interests
        software=software_by_role.get(role.id,[])
        matched=[link for link in software if link.skill_id in levels]
        unexplored=sorted((link for link in software if link.skill_id not in levels),key=lambda link:(not link.in_demand,not link.hot_technology,concepts[link.skill_id].canonical_name))[:3]
        def software_item(link):
            return {'skill_id':link.skill_id,'name':concepts[link.skill_id].canonical_name,'source_id':link.source_id,'in_demand':link.in_demand}
        technical={'status':'source_available' if software else 'no_source_associations','associated_count':len(software),
                   'matched_count':len(matched),'matched':[software_item(link) for link in sorted(matched,key=lambda link:concepts[link.skill_id].canonical_name)],
                   'explore':[software_item(link) for link in unexplored],
                   'note':'Published US software examples, not a checklist of mandatory tools. Matching a tool adds no broad readiness points; missing examples do not imply inability. Source flags are not current local demand.'}
        gaps = prioritize_gaps([{'skill_id':skill.id,'name':skill.canonical_name,'importance':link.required_importance,
                     'gap':round(1-levels.get(skill.id,0),2), 'critical':link.required_importance >= 4,
                     'priority':round(link.required_importance*(1-levels.get(skill.id,0)),4),
                     'development':'developing' if skill.id in levels else 'missing'}
                    for link,skill in requirements if levels.get(skill.id,0) < 1])
        relevance, discovery_reasons = discovery_relevance(role, requirements, targets, levels, technical)
        matches.append({'role_id':role.id,'title':role.title,'score':round(coverage*100,1),'coverage':round(coverage*100,1),
                        'discovery_relevance': relevance, 'discovery_reasons': discovery_reasons,
                        'limited_requirements': len(requirements) < 3,
                        'transferable_coverage':round(transfer*100,1),'interest_adjustment':0,'gaps':gaps,
                        'is_target':target,'context_alignment':alignment,'context_reasons':reasons,
                        'technical':technical,'assessment':assessment,'readiness_status':'self_reported' if recorded else 'not_assessed',
                        'selection_reason':'Your confirmed target; retained regardless of readiness.' if target else ' '.join(discovery_reasons) or 'No supported relevance connection yet.',
                        'explanation':f"Documented weighted coverage {coverage:.1%}: {len(recorded)} of {len(requirements)} important requirements recorded; {len(requirements)-len(recorded)} are unassessed, not proven weaknesses. Learning/working/strong self-ratings receive 25/65/100% credit, weighted by published importance. Interest and software add no coverage points. This is not an employability assessment.",
                        'source_ids':sorted({link.source_id for link,_ in requirements}|{link.source_id for link in software})})
    matches.sort(key=lambda m:(-m['technical']['matched_count'],-(m['score']+5*m['context_alignment']),-m['score'],m['title'],m['role_id']))
    result.update(status='ready' if matches else 'insufficient_profile_information',matches=matches if limit is None else select_directions(matches,limit))
    return result
