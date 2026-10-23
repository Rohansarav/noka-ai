
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app import market_api
from backend.app.synthetic_opportunities import collection

@pytest.mark.parametrize('market', ['MY', 'Global', 'All', 'US', 'SG'])
def test_every_category_and_pagination(market):
    result = collection(market, 'all', '', 0, 50)
    assert len(result['items']) == 13
    assert all(count > 0 for count in result['counts'].values())
    for category, count in result['counts'].items():
        filtered = collection(market, category, '', 0, 50)
        assert filtered['total'] == count
        assert all(category in row['categories'] for row in filtered['items'])
    assert len(collection(market, 'all', '', 12, 12)['items']) == 1
    found = collection(market, 'all', ' FORWARD DEPLOYED ', 0, 12)
    assert found['total'] == 1
    assert found['items'][0]['dimensions']['availability'] == 'reported_shortage'
    assert collection(market, 'all', 'nonexistentxyz', 0, 12)['total'] == 0

def test_http_contract_without_database_or_reviews(monkeypatch):
    def fail(*args):
        raise AssertionError('Synthetic view must not read reviewed evidence')
    monkeypatch.setattr(market_api, 'load_evidence', fail)
    app = FastAPI()
    app.include_router(market_api.router)
    app.dependency_overrides[market_api.get_session] = lambda: None
    with TestClient(app) as client:
        for market in ['All', 'MY', 'Global']:
            response = client.get('/api/opportunities', params={'review':'synthetic','market':market})
            assert response.status_code == 200
            payload = response.json()
            assert payload['total'] == 13
            for row in payload['items']:
                assert row['synthetic']
                assert 'not an observed' in row['assumption']
                assert row['baselines'][0]['source']['url'].startswith('https://')
                assert 'published_count' not in row
        assert client.get('/api/opportunities?review=synthetic&limit=0').status_code == 422
