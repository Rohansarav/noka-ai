import json
from pathlib import Path
import shutil
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.evidence_api import get_session
from backend.app.ingestion.parsers import DataValidationError, parse_indeed, parse_onet, parse_un
from backend.app.ingestion.runner import curation_fingerprint, import_all
from backend.app.models import Base, DemandObservation, IngestionRun, Role, RoleSkill, SDG, SDGTarget, Skill, Source

FIXTURE = Path(__file__).resolve().parents[2] / 'data/fixtures'
CURATION = Path(__file__).resolve().parents[2] / 'data/curation/catalogue.json'


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def seeded(db):
    import_all(db, FIXTURE, offline=True)
    return db


def test_real_indeed_rows_sorted_and_attributed():
    content = (FIXTURE/'indeed.csv').read_bytes()
    rows, skipped = parse_indeed(content)
    assert skipped == 141
    assert rows == sorted(rows, key=lambda r: (r['sector'], r['date']))
    assert rows[0]['country'] == 'US'
    assert rows[0]['indexed_value'] == 100
    assert rows[0]['adjusted_flag'] is True
    manifest = json.loads((FIXTURE/'manifest.json').read_text())
    assert manifest['indeed.csv']['is_subset']
    assert '/US/job_postings_by_sector_US.csv' in manifest['indeed.csv']['url']


@pytest.mark.parametrize('bad', ['', 'NaN', 'inf', '-1'])
def test_missing_or_invalid_index_rejected(bad):
    row = 'date,jobcountry,indeed_job_postings_index,variable,display_name\n2020-02-01,US,' + bad + ',total postings,Accounting\n'
    with pytest.raises(DataValidationError): parse_indeed(row.encode())


def test_schema_drift_rejected():
    with pytest.raises(DataValidationError): parse_indeed(b'date,country,index\n2020-02-01,US,100\n')


def test_unsorted_input_is_sorted_without_filling_values():
    lines = (FIXTURE/'indeed.csv').read_bytes().splitlines()
    reversed_source = b'\n'.join([lines[0], *reversed(lines[1:])])
    forward, _ = parse_indeed((FIXTURE/'indeed.csv').read_bytes())
    backward, _ = parse_indeed(reversed_source)
    assert forward == backward


def test_other_geographies_are_not_silently_substituted():
    content = (FIXTURE/'indeed.csv').read_bytes().replace(b',US,', b',MY,')
    with pytest.raises(DataValidationError): parse_indeed(content)


def test_duplicate_rows_are_deduplicated_but_conflicts_fail():
    lines = (FIXTURE/'indeed.csv').read_bytes().splitlines()
    data = b'\n'.join([lines[0], lines[1], lines[1]])
    rows, _ = parse_indeed(data)
    assert len(rows) == 1
    with pytest.raises(DataValidationError): parse_indeed(data + b'\n' + lines[1].replace(b',100,', b',101,'))


def test_un_all_17_goals_169_targets_with_verified_text():
    goals, targets = parse_un((FIXTURE/'un-goals.json').read_bytes())
    assert len(goals) == 17 and len(targets) == 169
    target = next(t for t in targets if t['id'] == '4.4')
    assert 'technical and vocational skills' in target['description']
    assert target['goal_id'] == 4
    with pytest.raises(DataValidationError): parse_un(b'[]')


def test_invalid_crosswalk_rejected():
    roles = json.loads(CURATION.read_text())['roles']
    roles[0]['sector'] = 'Invented Malaysian AI sector'
    observations, _ = parse_indeed((FIXTURE/'indeed.csv').read_bytes())
    with pytest.raises(DataValidationError):
        parse_onet((FIXTURE/'occupation_data.csv').read_bytes(), {'essential': (FIXTURE/'essential_skills.csv').read_bytes()}, roles, {r['sector'] for r in observations})


def test_human_approval_is_bound_to_reviewed_content():
    curation = json.loads(CURATION.read_text())
    assert curation['reviewed_content_sha256'] == curation_fingerprint(curation)
    curation['sdg_links'][0]['rationale'] = 'A later unreviewed edit'
    assert curation['reviewed_content_sha256'] != curation_fingerprint(curation)


def test_dry_run_makes_no_database_writes(db):
    result = import_all(db, FIXTURE, offline=True, dry_run=True)
    assert result['dry_run'] is True
    with Session(db) as session:
        assert session.scalar(select(func.count()).select_from(Source)) == 0
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 0


def test_idempotence_and_foreign_key_attribution(seeded):
    import_all(seeded, FIXTURE, offline=True)
    with Session(seeded) as session:
        for model, expected in [(Role,25),(Skill,35),(RoleSkill,875),(DemandObservation,141),(SDG,17),(SDGTarget,169),(Source,6)]:
            assert session.scalar(select(func.count()).select_from(model)) == expected
        for observation in session.scalars(select(DemandObservation)):
            source = session.get(Source, observation.source_id)
            assert source.license == 'CC BY 4.0'
            assert 'FIXTURE SUBSET' in source.notes
            assert source.retrieved_at.tzinfo
        assert session.get(Role,'17-2081.00').sector is None
        assert session.get(Role,'15-1252.00').sector == 'Software Development'


def test_failure_preserves_last_successful_rows(seeded, tmp_path):
    location = tmp_path/'corrupted'
    shutil.copytree(FIXTURE, location)
    (location/'indeed.csv').write_bytes(b'corrupted file')
    with pytest.raises(ValueError): import_all(seeded, location, offline=True)
    with Session(seeded) as session:
        assert session.scalar(select(func.count()).select_from(DemandObservation)) == 141
        assert session.scalar(select(func.count()).select_from(IngestionRun).where(IngestionRun.status=='failed')) == 1


def test_evidence_api_contracts(seeded):
    def session_override():
        with Session(seeded) as session: yield session
    app.dependency_overrides[get_session] = session_override
    try:
        with TestClient(app) as client:
            summary = client.get('/api/datasets/summary').json()
            assert summary['counts']['sdgs'] == 17
            assert summary['start_date'] == '2020-02-01'
            assert summary['end_date'] == '2020-02-03'
            assert len(summary['last_successful_imports']) == 4
            roles = client.get('/api/roles').json()['roles']
            assert len(roles) == 25
            assert all(r['individual_statistically_forecastable'] is False for r in roles)
            detail = client.get('/api/roles/15-1252.00').json()
            assert len(detail['skills']) == 35
            assert detail['source']['license'] == 'CC BY 4.0'
            assert len(client.get('/api/skills').json()['skills']) == 35
            history = client.get('/api/demand/history', params={'sector':'Software Development'}).json()
            assert history['baseline'] == '2020-02-01 = 100'
            assert [p['date'] for p in history['points']] == sorted(p['date'] for p in history['points'])
            assert client.get('/api/demand/history?sector=Nonexistent').status_code == 404
            assert client.get('/api/demand/history?sector=Accounting&start=2026-01-01&end=2020-01-01').status_code == 422
            assert client.get('/api/roles/unknown').status_code == 404
            sdgs = client.get('/api/sdgs').json()
            assert len(sdgs['goals']) == 17
            assert sum(len(g['targets']) for g in sdgs['goals']) == 169
            assert sum(len(t['links']) for g in sdgs['goals'] for t in g['targets']) == 7
    finally:
        app.dependency_overrides.clear()
