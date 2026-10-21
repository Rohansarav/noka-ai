"""Bounded public catalogue discovery; search hints never establish occupation equivalence."""
import re
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.evidence_api import get_session
from backend.app.occupation_catalogue import occupation_evidence

router = APIRouter(prefix='/api/careers', tags=['Career discovery'])
# Noka discovery hints, not O*NET aliases or automatic mappings. Users confirm interpretations.
HINTS = {
    'ai': ['Data Scientists', 'Software Developers', 'Computer and Information Research Scientists'],
    'artificial intelligence': ['Data Scientists', 'Software Developers', 'Computer and Information Research Scientists'],
    'machine learning': ['Data Scientists', 'Software Developers', 'Computer and Information Research Scientists'],
    'ml': ['Data Scientists', 'Software Developers'],
    'ux': ['Web and Digital Interface Designers', 'Human Factors Engineers and Ergonomists'],
    'cybersecurity': ['Information Security Analysts'],
    'product manager': ['Marketing Managers', 'Computer and Information Systems Managers', 'Project Management Specialists'],
}


def words(value):
    return set(re.findall(r'[a-z0-9]{2,}', value.casefold()))


@router.get('')
def discover(q: str = Query(default='', max_length=120), family: str = Query(default='', pattern=r'^(|\d{2})$'),
             offset: int = Query(default=0, ge=0, le=5000), limit: int = Query(default=20, ge=1, le=50), db: Session = Depends(get_session)):
    roles = occupation_evidence(db)[0]
    tokens = words(q)
    hints = {title for phrase, titles in HINTS.items() if words(phrase) <= tokens for title in titles} if tokens else set()
    found = []
    for role in roles:
        if q.strip() and not tokens:
            continue
        if family and not role.occupation_code.startswith(family):
            continue
        title_tokens, all_tokens = words(role.title), words(role.title+' '+role.description)
        if tokens and not (tokens <= all_tokens or role.title in hints):
            continue
        score = (100 if q.strip().casefold() == role.title.casefold() else 0) + len(tokens & title_tokens)*5 + (3 if role.title in hints else 0)
        found.append((score, role))
    found.sort(key=lambda row: (-row[0], row[1].title, row[1].id))
    return {'total': len(found), 'offset':offset, 'limit':limit,
            'families': sorted({r.occupation_code[:2] for r in roles}),
            'roles':[{'id':r.id, 'title':r.title, 'description':r.description, 'family':r.occupation_code[:2],
                      'source_id':r.source_id, 'match_reason':'Noka search hint; confirm this interpretation' if r.title in hints else 'Catalogue title or description match'}
                     for _,r in found[offset:offset+limit]],
            'method':'Source-backed US occupations. Search hints suggest interpretations; they are not verified aliases or local vacancy evidence.'}
