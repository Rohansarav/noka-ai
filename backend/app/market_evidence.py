"""Typed public opportunity evidence. Profile proficiency never receives market points."""
from datetime import date, datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
import hashlib
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from sqlalchemy import select
from backend.app.models import IntelligenceRecord, Role

UNKNOWN = 'insufficient_evidence'
KINDS = {'sources': 'market_source', 'mappings': 'market_mapping', 'claims': 'market_claim'}
CATEGORIES = ['growing', 'declining', 'stable', 'emerging', 'transforming', 'reported_shortage']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Review(Strict):
    status: Literal['pending_review', 'approved', 'rejected'] = 'pending_review'
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    reason: str | None = None

    @model_validator(mode='after')
    def signed(self):
        if self.status != 'pending_review' and (not self.reviewer or not self.reviewed_at or not self.reason):
            raise ValueError('A review needs a reviewer, timestamp and reason')
        return self

class MarketSource(Strict):
    id: str
    title: str
    publisher: str
    url: str
    market: str
    publication_date: date | None = None
    retrieved_at: datetime
    version: str
    coverage: str
    access: str
    refresh: str
    reuse: str
    limitation: str
    content_hash: str | None = None

    @field_validator('url')
    @classmethod
    def https(cls, value):
        p = urlsplit(value)
        if p.scheme != 'https' or not p.hostname or p.username or p.password:
            raise ValueError('Public HTTPS source required')
        return value

class OccupationMapping(Strict):
    id: str
    role_id: str
    occupation_code: str
    occupation_title: str
    taxonomy: str
    family: str
    source_id: str
    locator: str
    relationship: Literal['equivalent', 'source_broader', 'source_narrower', 'uncertain']
    rationale: str = Field(min_length=30)
    limitations: str = Field(min_length=10)
    review: Review = Field(default_factory=Review)

class MarketClaim(Strict):
    id: str
    source_id: str
    occupation_code: str
    taxonomy: str
    market: str
    dimension: Literal['demand', 'change', 'availability']
    category: Literal['growing', 'declining', 'stable', 'emerging', 'transforming', 'reported_shortage']
    basis: Literal['observed_comparison', 'employer_projection', 'task_study', 'shortage_list']
    observation_period: str = Field(min_length=4)
    horizon: str | None = None
    locator: str = Field(min_length=3)
    statement: str = Field(min_length=20, max_length=1600)
    valid_until: date
    review: Review = Field(default_factory=Review)

    @model_validator(mode='after')
    def classification(self):
        allowed = {'demand': {'growing', 'declining', 'stable'}, 'change': {'emerging', 'transforming'}, 'availability': {'reported_shortage'}}
        if self.category not in allowed[self.dimension]:
            raise ValueError('Category and dimension disagree')
        if self.dimension == 'demand' and self.basis not in {'observed_comparison', 'employer_projection'}:
            raise ValueError('Shortage or task change cannot establish growth')
        if self.dimension == 'change' and self.basis == 'shortage_list':
            raise ValueError('Shortage alone cannot establish occupational change')
        if self.dimension == 'availability' and self.basis != 'shortage_list':
            raise ValueError('Shortage evidence required')
        if self.basis == 'employer_projection' and not self.horizon:
            raise ValueError('Projection horizon required')
        return self

class EvidenceBundle(Strict):
    sources: list[MarketSource]
    mappings: list[OccupationMapping]
    claims: list[MarketClaim]

    @model_validator(mode='after')
    def references(self):
        for rows in (self.sources, self.mappings, self.claims):
            if len({r.id for r in rows}) != len(rows):
                raise ValueError('Duplicate evidence ID')
        sources = {s.id: s for s in self.sources}
        for row in [*self.mappings, *self.claims]:
            if row.source_id not in sources:
                raise ValueError('Unknown source')
        for c in self.claims:
            if c.market != sources[c.source_id].market:
                raise ValueError('Claim geography differs from publication')
            if not any(m.occupation_code == c.occupation_code and m.taxonomy == c.taxonomy for m in self.mappings):
                raise ValueError('Unmapped source occupation')
        return self

def load_evidence(db):
    """One public-store read; tolerate unrelated legacy records, never truncate coverage."""
    groups = {k: [] for k in KINDS}
    schemas = {'sources': MarketSource, 'mappings': OccupationMapping, 'claims': MarketClaim}
    reverse = {v: k for k, v in KINDS.items()}
    for record in db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.kind.in_(reverse))):
        key = reverse[record.kind]
        groups[key].append(schemas[key].model_validate(record.payload).model_dump(mode='json'))
    return groups

def import_bundle(db, raw):
    """Validate the entire import before writing; caller transaction preserves last success."""
    bundle = EvidenceBundle.model_validate(raw)
    roles = set(db.scalars(select(Role.id)))
    if any(m.role_id not in roles for m in bundle.mappings):
        raise ValueError('Mapping references an unknown Noka occupation')
    now = datetime.now(timezone.utc)
    changed = 0
    for key, kind in KINDS.items():
        for row in getattr(bundle, key):
            rid = hashlib.sha256(f'{kind}:{row.id}'.encode()).hexdigest()
            payload = row.model_dump(mode='json')
            old = db.get(IntelligenceRecord, rid)
            if old and old.payload == payload:
                continue
            # Import must never silently overwrite a recorded editorial decision.
            if old and old.payload.get('review', {}).get('status') in {'approved', 'rejected'}:
                if {k:v for k,v in old.payload.items() if k!='review'} == {k:v for k,v in payload.items() if k!='review'}:
                    continue
                raise ValueError('Reviewed content is immutable; import a new version ID')
            db.merge(IntelligenceRecord(id=rid, kind=kind, payload=payload, created_at=now))
            changed += 1
    db.flush()
    return {'changed': changed, 'sources': len(bundle.sources), 'mappings': len(bundle.mappings), 'claims': len(bundle.claims)}

def role_outlook(role_id, market, evidence, today=None):
    """Approval, freshness and occupation scope gate every published label independently."""
    today = today or date.today()
    sources = {s['id']: s for s in evidence['sources']}
    mappings = [m for m in evidence['mappings'] if m['role_id'] == role_id]
    items = []
    for m in mappings:
        for c in evidence['claims']:
            if c['occupation_code'] != m['occupation_code'] or c['taxonomy'] != m['taxonomy']:
                continue
            if c['market'] not in {market, 'Global'} and market != 'All':
                continue
            rejected = 'rejected' in {c['review']['status'], m['review']['status']}
            if rejected:
                continue
            stale = date.fromisoformat(c['valid_until']) < today
            approved = all(r['review']['status'] == 'approved' for r in (c,m)) and m['relationship'] != 'uncertain'
            state = 'stale' if stale else 'published' if approved else 'pending_review'
            items.append({**c, 'mapping': m, 'source': sources[c['source_id']], 'state': state,
                          'scope': 'local' if c['market'] == market else 'global_context',
                          'current': approved and not stale})
    items.sort(key=lambda c: (c['market'] != market, not c['current'], c['id']))
    dimensions = {}
    for dim in ('demand', 'change', 'availability'):
        relevant = [c for c in items if c['current'] and c['dimension'] == dim]
        local = [c for c in relevant if c['market'] == market]
        candidates = local or relevant
        labels = sorted({c['category'] for c in candidates})
        # Conflicting directions are explicit, never averaged into a reassuring label.
        contexts = {}
        for c in candidates:
            key = (c['market'], c['observation_period'], c['horizon'], c['basis'])
            contexts.setdefault(key, set()).add(c['category'])
        conflicting = dim == 'demand' and any(len(values)>1 for values in contexts.values())
        geographies = sorted({c['market'] for c in candidates})
        dimensions[dim] = {'labels': labels, 'status': 'conflicting' if conflicting else 'supported' if labels else UNKNOWN,
                           'market': geographies[0] if len(geographies)==1 else 'Multiple geographies' if geographies else None}
    return {'role_id': role_id, 'market': market, 'dimensions': dimensions, 'evidence': items,
            'mappings': mappings, 'published_count': sum(c['current'] for c in items),
            'pending_count': sum(c['state'] == 'pending_review' for c in items),
            'limitation': 'Occupation mappings retain their scope. Opportunity evidence does not change documented capability coverage or predict hiring.'}
