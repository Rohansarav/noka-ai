"""Workload routing is independent of the legacy Scout model setting."""
from backend.app.config import Settings


def test_model_defaults_and_environment_overrides(monkeypatch):
    for key in ('OPENAI_MODEL', 'OPENAI_EXTRACTION_MODEL', 'OPENAI_GUIDE_MODEL'):
        monkeypatch.delenv(key, raising=False)
    defaults = Settings(_env_file=None)
    assert defaults.openai_extraction_model == 'gpt-4.1-mini'
    assert defaults.openai_guide_model == 'gpt-6-sol'
    monkeypatch.setenv('OPENAI_MODEL', 'scout-only')
    monkeypatch.setenv('OPENAI_EXTRACTION_MODEL', 'extraction-override')
    monkeypatch.setenv('OPENAI_GUIDE_MODEL', 'guide-override')
    configured = Settings(_env_file=None)
    assert configured.openai_model == 'scout-only'
    assert configured.openai_extraction_model == 'extraction-override'
    assert configured.openai_guide_model == 'guide-override'
