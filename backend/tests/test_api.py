from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from backend.app import main


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE alembic_version (version_num TEXT)")
        conn.exec_driver_sql("INSERT INTO alembic_version VALUES ('0006')")
    monkeypatch.setattr(main, "engine", engine)
    with TestClient(main.app) as test_client:
        yield test_client
    engine.dispose()


def test_health(client):
    assert client.get('/api/health').json() == {"status": "ok", "service": "noka-api"}


def test_ready(client):
    assert client.get('/api/ready').status_code == 200


def test_unmigrated_database(client):
    with main.engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM alembic_version")
    response = client.get('/api/ready')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'schema_unavailable'


def test_unknown_api_is_not_spa(client):
    response = client.get('/api/unknown')
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'not_found'


@pytest.mark.parametrize('path', ['/', '/profile', '/forecast', '/design-preview', '/profile/intake'])
def test_production_routes(client, path):
    assert (main.DIST / 'index.html').is_file(), 'Run pnpm build before API tests'
    response = client.get(path)
    assert response.status_code == 200
    assert '<div id="root">' in response.text


def test_missing_asset(client):
    assert client.get('/assets/missing.js').status_code == 404


def test_production_requires_frontend(client, monkeypatch, tmp_path):
    from backend.app.config import Settings
    monkeypatch.setattr(main, 'get_settings', lambda: Settings(environment='production'))
    monkeypatch.setattr(main, 'DIST', tmp_path)
    response = client.get('/api/ready')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'frontend_unavailable'


def test_database_failure_does_not_leak_details(client, monkeypatch):
    def fail():
        raise RuntimeError('private database credentials')
    monkeypatch.setattr(main.engine, 'connect', fail)
    response = client.get('/api/ready')
    assert response.status_code == 503
    assert 'private' not in response.text
