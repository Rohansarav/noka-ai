"""Opportunity labels must survive missing data, review gates and conflicting sources."""
import copy, json
from datetime import date
from pathlib import Path
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.app.models import Base, IntelligenceRecord
from backend.app.ingestion.runner import import_all
from backend.app.market_evidence import EvidenceBundle, MarketClaim, Review, import_bundle, role_outlook, load_evidence
from backend.app.market_research import proposal_bundle

@pytest.fixture
def evidence():
    raw=json.loads(Path('data/market/baseline.json').read_text(encoding='utf-8'))
    return EvidenceBundle.model_validate(raw).model_dump(mode='json')

def approve(e):
    for r in e['mappings']+e['claims']:
        r['review']={'status':'approved','reviewer':'Test reviewer','reviewed_at':'2026-10-22T00:00:00Z','reason':'Fixture review only'}

def test_pending_is_not_published_and_market_scopes_are_separate(evidence):
    result=role_outlook('15-1252.00','MY',evidence,date(2026,10,22))
    assert result['pending_count']==2 and result['published_count']==0
    assert all(d['status']=='insufficient_evidence' for d in result['dimensions'].values())
    assert result['evidence'][0]['market']=='MY'
    approve(evidence)
    result=role_outlook('15-1252.00','MY',evidence,date(2026,10,22))
    assert result['dimensions']['demand']['labels']==['growing']
    assert result['dimensions']['demand']['market']=='Global'
    assert result['dimensions']['availability']['labels']==['reported_shortage']
    assert result['dimensions']['availability']['market']=='MY'
    other=role_outlook('15-1252.00','SG',evidence,date(2026,10,22))
    assert all(c['market']=='Global' for c in other['evidence'])
    assert other['dimensions']['availability']['labels']==[]

def test_stale_rejected_and_uncertain_never_publish(evidence):
    approve(evidence)
    stale=role_outlook('15-1252.00','MY',evidence,date(2028,1,1))
    assert stale['published_count']==0 and all(c['state']=='stale' for c in stale['evidence'])
    for m in evidence['mappings']:m['relationship']='uncertain'
    assert role_outlook('15-1252.00','MY',evidence,date(2026,10,22))['published_count']==0
    for m in evidence['mappings']:m['review']['status']='rejected'
    assert not role_outlook('15-1252.00','MY',evidence,date(2026,10,22))['evidence']

def test_conflicting_demands_are_not_averaged(evidence):
    approve(evidence)
    c=copy.deepcopy(next(c for c in evidence['claims'] if c['id']=='wef25-15-1252.00-growing'))
    c['id']='conflicting-fixture';c['category']='declining';evidence['claims'].append(c)
    d=role_outlook('15-1252.00','MY',evidence,date(2026,10,22))['dimensions']['demand']
    assert d['status']=='conflicting' and d['labels']==['declining','growing']

def test_classification_and_review_contract(evidence):
    c=copy.deepcopy(evidence['claims'][0]);c.update(category='growing',dimension='demand')
    with pytest.raises(ValidationError):MarketClaim.model_validate(c)
    with pytest.raises(ValidationError):Review(status='approved')
    c.update(basis='employer_projection',horizon=None)
    with pytest.raises(ValidationError):MarketClaim.model_validate(c)
    evidence['claims'][0]['market']='Global'
    with pytest.raises(ValidationError):EvidenceBundle.model_validate(evidence)

def test_atomic_import_and_deduplication(evidence):
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine);import_all(engine,Path('data/fixtures'),offline=True)
    with Session(engine) as db:
        # The fixture catalogue is deliberately smaller than production.
        from backend.app.models import Role
        ids=set(db.scalars(select(Role.id)))
        evidence['mappings']=[m for m in evidence['mappings'] if m['role_id'] in ids]
        keys={(m['taxonomy'],m['occupation_code']) for m in evidence['mappings']}
        evidence['claims']=[c for c in evidence['claims'] if (c['taxonomy'],c['occupation_code']) in keys]
        first=import_bundle(db,evidence);db.commit()
        assert first['changed']>0
        assert import_bundle(db,evidence)['changed']==0
        db.commit()
        before=load_evidence(db)
        invalid=copy.deepcopy(evidence);invalid['mappings'][0]['role_id']='made-up'
        with pytest.raises(ValueError):import_bundle(db,invalid)
        db.rollback()
        assert load_evidence(db)==before

def test_research_requires_verbatim_grounding(evidence):
    m=evidence['mappings'][0]
    finding={'url':'https://www.talentcorp.com.my/test','title':'Test publication'}
    text='Malaysia 2025-2030: Computer systems analysts are expected to grow in employer projections.'
    p={'mapping_id':m['id'],'market':'MY','category':'growing','basis':'employer_projection','quote':text,'observation_period':'2025','horizon':'2025-2030','explanation':'Employer projections describe expected growth in the stated period.','mapping_rationale':'The publication explicitly names the computer systems analyst occupation.','relationship':'source_broader'}
    result=proposal_bundle(finding,text,[m],{'claims':[p]})
    assert result['claims'][0]['review']['status']=='pending_review'
    p['quote']='This invented quotation was never in the publication.'
    with pytest.raises(ValueError):proposal_bundle(finding,text,[m],{'claims':[p]})
    p['quote']=text;p['mapping_id']='invented'
    with pytest.raises(ValueError):proposal_bundle(finding,text,[m],{'claims':[p]})

def test_independent_dimensions_allow_transformation_and_shortage(evidence):
    approve(evidence)
    row=role_outlook('13-2011.00','MY',evidence,date(2026,10,22))
    assert row['dimensions']['change']['labels']==['transforming']
    assert row['dimensions']['availability']['labels']==['reported_shortage']
    assert row['dimensions']['demand']['market']=='Global'

def test_market_api_pagination_and_validation(evidence):
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    from backend.app.main import app
    from backend.app.evidence_api import get_session
    from backend.app.models import Role
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine);import_all(engine,Path('data/fixtures'),offline=True)
    with Session(engine) as db:
        ids=set(db.scalars(select(Role.id)))
        evidence['mappings']=[m for m in evidence['mappings'] if m['role_id'] in ids]
        keys={(m['taxonomy'],m['occupation_code']) for m in evidence['mappings']}
        evidence['claims']=[c for c in evidence['claims'] if (c['taxonomy'],c['occupation_code']) in keys]
        import_bundle(db,evidence);db.commit()
    def session():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_session]=session
    try:
        with TestClient(app) as client:
            first=client.get('/api/opportunities?limit=1').json()
            second=client.get('/api/opportunities?limit=1&offset=1').json()
            assert first['total']>1
            assert first['counts']==second['counts']
            assert first['items'][0]['role_id']!=second['items'][0]['role_id']
            assert client.get('/api/opportunities?review=published').json()['total']==0
            assert client.get('/api/opportunities?category=emerging').json()['total']==0
            assert client.get('/api/opportunities?limit=1000').status_code==422
            assert client.get('/api/opportunities/roles/missing').status_code==404
            assert client.get('/api/opportunities/roles/15-1252.00?market=SG').json()['evidence'][0]['market']=='Global'
    finally:app.dependency_overrides.clear()


def test_source_country_does_not_leak_between_all_market_dimensions(evidence):
    approve(evidence)
    row=role_outlook('15-1252.00','All',evidence,date(2026,10,22))
    assert row['dimensions']['availability']['market']=='MY'
    assert row['dimensions']['demand']['market']=='Global'

def test_reviewed_content_survives_repeat_import(evidence):
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    import_all(engine,Path('data/fixtures'),offline=True)
    from backend.app.models import Role
    with Session(engine) as db:
        ids=set(db.scalars(select(Role.id)))
        evidence['mappings']=[m for m in evidence['mappings'] if m['role_id'] in ids]
        keys={(m['taxonomy'],m['occupation_code']) for m in evidence['mappings']}
        evidence['claims']=[c for c in evidence['claims'] if (c['taxonomy'],c['occupation_code']) in keys]
        approved=copy.deepcopy(evidence);approve(approved)
        import_bundle(db,approved);db.commit()
        assert import_bundle(db,evidence)['changed']==0
        db.commit()
        assert all(m['review']['status']=='approved' for m in load_evidence(db)['mappings'])
        evidence['claims'][0]['statement']='Changed interpretation requiring a new version.'
        with pytest.raises(ValueError):import_bundle(db,evidence)
        db.rollback()
        assert all(m['review']['status']=='approved' for m in load_evidence(db)['mappings'])
