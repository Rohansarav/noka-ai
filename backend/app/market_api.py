"""Public, paginated opportunity comparisons. Editorial writes are operator-only CLI."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.evidence_api import get_session
from backend.app.models import Role
from backend.app.market_evidence import CATEGORIES, load_evidence, role_outlook
from backend.app.profile_security import same_origin, active_session

router = APIRouter(prefix='/api/opportunities', tags=['Opportunity evidence'])


@router.post('/roles/{role_id}/work-changes', dependencies=[Depends(same_origin)])
def work_changes(role_id: str, request: Request, market: str = Query('MY', pattern=r'^(MY|US|GB|SG|AU|OTHER|Global|All)$'), db: Session = Depends(get_session)):
    """Generate on explicit request, for an existing private session only."""
    owner = active_session(request, db)
    if not owner:
        raise HTTPException(401)
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404)
    from backend.app.config import get_settings
    from backend.app.work_changes import interpret, allow_request
    if not allow_request(owner.token_hash):
        return {'status': 'unavailable', 'message': 'Interpretation request limit reached. Please try again in an hour.'}
    return interpret(role, role_outlook(role_id, market, load_evidence(db)), get_settings())

@router.get('')
def opportunities(market: str = Query('MY', pattern=r'^(MY|US|GB|SG|AU|OTHER|Global|All)$'),
                  category: str = Query('all', pattern=r'^(all|growing|declining|stable|emerging|transforming|reported_shortage|insufficient_evidence)$'),
                  review: Literal['all','published','pending_review','stale','synthetic'] = 'published',
                  search: str = Query('', max_length=120), offset: int = Query(0, ge=0),
                  limit: int = Query(12, ge=1, le=50), db: Session = Depends(get_session)):
    if review == 'synthetic':
        from backend.app.synthetic_opportunities import collection
        return collection(market, category, search, offset, limit)
    evidence = load_evidence(db)
    role_ids = {m['role_id'] for m in evidence['mappings']}
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids)).order_by(Role.title)).all()
    rows = []
    for role in roles:
        r = {**role_outlook(role.id, market, evidence), 'title': role.title}
        if search.casefold() not in role.title.casefold():
            continue
        # A market view includes only relevant evidence, rather than unrelated mappings.
        if not r['evidence']:
            continue
        r['visible_evidence'] = [e for e in r['evidence'] if review == 'all' or e['state'] == review]
        if r['visible_evidence']:
            rows.append(r)
    counts = {c: sum(any(e['category'] == c for e in r['visible_evidence']) for r in rows) for c in CATEGORIES}
    counts['insufficient_evidence'] = sum(not r['published_count'] for r in rows)
    filtered = [r for r in rows if category == 'all' or (category == 'insufficient_evidence' and not r['published_count']) or any(e['category'] == category for e in r['visible_evidence'])]
    for r in filtered:
        r['evidence'] = r.pop('visible_evidence')
    return {'items': filtered[offset:offset+limit], 'total': len(filtered), 'offset': offset, 'limit': limit,
            'counts': counts, 'covered_roles': len(rows), 'catalogue_roles': db.scalar(select(func.count()).select_from(Role)),
            'sources': evidence['sources'], 'method': 'Counts describe evidence records in this view, including proposals when selected. Only fresh claims with approved occupation mappings publish a label. Shortage is separate from growth.'}

@router.get('/roles/{role_id}')
def opportunity(role_id: str, market: str = Query('MY', pattern=r'^(MY|US|GB|SG|AU|OTHER|Global|All)$'), db: Session = Depends(get_session)):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404)
    return {**role_outlook(role_id, market, load_evidence(db)), 'title': role.title}
