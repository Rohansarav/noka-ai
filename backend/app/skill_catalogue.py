"""Bounded catalogue search and source-specific resolution for profiles and extraction."""
import re
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from backend.app.evidence_api import get_session
from backend.app.occupation_catalogue import skill_evidence
from backend.app.models import Source
from sqlalchemy import select

router=APIRouter(prefix='/api/skill-catalogue',tags=['Skill discovery'])
MAX_MODEL_CANDIDATES=120


def term_match(text,term):
    suffix=r'(?![\w+#])' if term.casefold()=='c' else r'(?!\w)'
    return re.search(r'(?<!\w)'+re.escape(term)+suffix,text,re.I)


def retrieve_candidates(text,skills):
    """Keep all broad concepts plus the strongest literal software matches, bounded for the LLM."""
    lower=text.casefold()
    broad=[s for s in skills if s.category!='software']
    found=[]
    for skill in skills:
        if skill.category!='software':continue
        hits=[term for term in (skill.canonical_name,*skill.aliases) if term.casefold() in lower and term_match(text,term)]
        if hits:found.append((max(len(term) for term in hits),skill))
    found.sort(key=lambda row:(-row[0],row[1].canonical_name))
    return broad[:MAX_MODEL_CANDIDATES]+[s for _,s in found[:max(0,MAX_MODEL_CANDIDATES-len(broad))]]


@router.get('')
def search_skills(q:str=Query(default='',max_length=120),category:str=Query(default='all',pattern='^(all|core|software)$'),
                  ids:str=Query(default='',max_length=3000),roles:str=Query(default='',max_length=500),offset:int=Query(default=0,ge=0,le=20000),
                  limit:int=Query(default=20,ge=1,le=50),db:Session=Depends(get_session)):
    skills,associations=skill_evidence(db)
    wanted={v for v in ids.split(',') if v}
    if len(wanted)>60:raise HTTPException(422,detail='At most 60 selected skills.')
    target_ids={v for v in roles.split(',') if v}
    relevant={a.skill_id for a in associations if a.role_id in target_ids}
    words=set(re.findall(r'[\w+#.]+',q.casefold()))
    matches=[]
    for skill in skills.values():
        if q.strip() and not words:continue
        if wanted and skill.id not in wanted:continue
        if category!='all' and (skill.category=='software')!=(category=='software'):continue
        names=[skill.canonical_name.casefold(),*(a.casefold() for a in skill.aliases)]
        if q.strip() and not any(all(word in name for word in words) for name in names):continue
        exact=q.casefold().strip() in names
        matches.append((not exact,skill.id not in relevant,skill.canonical_name,skill))
    matches.sort(key=lambda row:row[:3])
    sources={s.id:s for s in db.scalars(select(Source).where(Source.id.in_({s.source_id for *_,s in matches[offset:offset+limit]})))}
    return {'skills':[{'id':s.id,'canonical_name':s.canonical_name,'aliases':list(s.aliases),'category':s.category,'source_id':s.source_id,'source_url':sources[s.source_id].canonical_url,'source_version':sources[s.source_id].version,'relevant_to_targets':s.id in relevant} for *_,s in matches[offset:offset+limit]],
            'catalogue_total':len(skills),'matched_total':len(matches),'offset':offset,'limit':limit,
            'counts':{'core':sum(s.category!='software' for s in skills.values()),'software':sum(s.category=='software' for s in skills.values())},
            'method':'Broad skills use rated occupational requirements. Software concepts use published associations, not importance ratings. Custom skills are saved separately and do not create evidence.'}
