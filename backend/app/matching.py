"""Explainable readiness, explicit aspirations and source-bound development priorities."""
import re
from sqlalchemy import select
from backend.app.models import ProfileSkill
from backend.app.occupation_catalogue import occupation_evidence, skill_evidence

LEVELS = {'learning': .25, 'working': .65, 'strong': 1.0}
METHOD = ('Documented coverage = sum(O*NET importance × self-rated level) / sum(importance) × 100, using importance ≥3/5. '
          'Levels: learning .25, working .65, strong 1. Interests do not increase readiness. '
          'Software alignment counts distinct published occupation associations separately; tools add no broad readiness credit. Discovery orders by matched software count, then readiness plus context. All supported occupations are ranked before display; up to five explicit targets are retained alongside five discoveries. '
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
    discoveries = [m for m in matches if not m['is_target'] and (m['score']>0 or m['context_alignment']>0 or m.get('technical',{}).get('matched_count',0)>0)][:limit]
    return targets + discoveries


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
        matches.append({'role_id':role.id,'title':role.title,'score':round(coverage*100,1),'coverage':round(coverage*100,1),
                        'transferable_coverage':round(transfer*100,1),'interest_adjustment':0,'gaps':gaps,
                        'is_target':target,'context_alignment':alignment,'context_reasons':reasons,
                        'technical':technical,'assessment':assessment,'readiness_status':'self_reported' if recorded else 'not_assessed',
                        'selection_reason':'Your confirmed target; retained regardless of readiness.' if target else 'Discovered from all supported occupations using readiness and separate context relevance.',
                        'explanation':f"Documented weighted coverage {coverage:.1%}: {len(recorded)} of {len(requirements)} important requirements recorded; {len(requirements)-len(recorded)} are unassessed, not proven weaknesses. Learning/working/strong self-ratings receive 25/65/100% credit, weighted by published importance. Interest and software add no coverage points. This is not an employability assessment.",
                        'source_ids':sorted({link.source_id for link,_ in requirements}|{link.source_id for link in software})})
    matches.sort(key=lambda m:(-m['technical']['matched_count'],-(m['score']+5*m['context_alignment']),-m['score'],m['title'],m['role_id']))
    result.update(status='ready' if matches else 'insufficient_profile_information',matches=matches if limit is None else select_directions(matches,limit))
    return result
