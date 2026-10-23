from backend.app.pathway_exercises import exercise, DELIVERABLES
from backend.app.future import PRACTICE


def test_supported_skills_have_distinct_deliverables():
    assert set(PRACTICE) <= set(DELIVERABLES)
    assert len(set(DELIVERABLES.values())) == len(DELIVERABLES)
    for name,(activity,project) in PRACTICE.items():
        value=exercise(name,'Systems Architect',activity,project)
        assert len(value['task_steps']) >= 3
        assert len(value['acceptance_criteria'])==3
        assert 'Begin with a short independent attempt' not in ' '.join(value['task_steps'])


def test_monitoring_and_reading_have_actionable_and_different_outputs():
    monitor=exercise('Monitoring','Systems Architect','','')
    reading=exercise('Reading Comprehension','Systems Architect','','')
    assert 'threshold' in ' '.join(monitor['task_steps'])
    assert 'simulated' in monitor['project']
    assert 'annotate' in ' '.join(reading['task_steps'])
    assert 'Systems Architect' in reading['task_steps'][0]
    assert 'supporting passages' in reading['project']
