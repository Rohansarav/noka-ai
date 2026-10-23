"""Illustrative career records for Atlas only; never imported as observed evidence."""
SCENARIOS = [
    ('Forward Deployed Engineer', 'emerging', 'Adapt AI applications to client workflows, evaluate reliability and coordinate deployment.', ['Requirements discovery', 'API integration', 'AI evaluation']),
    ('Administrative Assistant', 'declining', 'Assume routine drafting is automated; verification and exception handling become more prominent.', ['Data validation', 'Workflow automation', 'Communication']),
    ('AI Evaluation Specialist', 'emerging', 'Design evaluation cases, investigate failures and document model limitations.', ['Test design', 'Error analysis', 'Python']),
    ('Software Developer', 'transforming', 'Use generated code while taking responsibility for tests, security and maintainability.', ['Code review', 'Automated testing', 'Security']),
    ('Customer Support Specialist', 'transforming', 'Review suggested answers and handle ambiguous or sensitive escalations.', ['Quality assurance', 'Escalation design', 'Communication']),
    ('Learning Designer', 'transforming', 'Evaluate generated materials for accuracy, accessibility and learning outcomes.', ['Instructional design', 'Accessibility', 'Evaluation']),
]



# Each tuple describes authored assumptions across independent Atlas dimensions.
EXTRA = [
 ('Cybersecurity Analyst', 'growing', 'Investigate AI-assisted threats and validate security controls.', ['Threat analysis', 'Security testing']),
 ('Data Engineer', 'growing', 'Build reliable datasets for AI applications.', ['SQL', 'Data quality']),
 ('Records Clerk', 'declining', 'Validate automated document classification and resolve exceptions.', ['Records governance', 'Quality checks']),
 ('Facilities Coordinator', 'stable', 'Coordinate physical maintenance while using scheduling assistants.', ['Coordination', 'Safety']),
 ('Community Liaison', 'stable', 'Maintain community relationships and verify generated communications.', ['Speaking', 'Stakeholder engagement']),
 ('AI Safety Research Coordinator', 'insufficient_evidence', 'Explore possible evaluation responsibilities without assuming demand direction.', ['Research literacy', 'Evaluation']),
 ('Human-AI Interaction Researcher', 'insufficient_evidence', 'Study user needs while role boundaries remain uncertain in this scenario.', ['User research', 'Experiment design']),
]
SCENARIOS += EXTRA

BASELINES = [{'statement': 'Published jobs-outlook context used as inspiration; all scenario-specific classifications, tasks and skills below are authored assumptions.', 'source': {'id': 'wef-jobs-2025', 'title': 'Future of Jobs Report 2025: Jobs outlook', 'publisher': 'World Economic Forum', 'url': 'https://www.weforum.org/publications/the-future-of-jobs-report-2025/2-jobs-outlook', 'market': 'Global', 'publication_date': '2025-01-07', 'retrieved_at': '2026-10-22T05:27:26.480544+00:00', 'version': '2025', 'coverage': 'Global employer expectations for 2025-2030.', 'access': 'Existing Noka crosswalk retained as pending proposal.', 'refresh': 'Publication driven; editorial recheck within 180 days.', 'reuse': 'Derived factual metadata and paraphrases only; original publication is linked. Redistribution rights not established.', 'limitation': 'Global projections are not Malaysian observed employment or hiring probabilities.'}}]

def collection(market, category, search, offset, limit):
    """Serve a bundled demo independently of database reviews or network access.

    All scenarios have global illustrative scope, so each supported market includes
    the same global context; none imply a local labour-market observation.
    """
    rows = []
    for index, (title, direction, tasks, skills) in enumerate(SCENARIOS):
        if search.strip().casefold() not in title.casefold():
            continue
        demand = direction if direction in {'growing', 'declining', 'stable'} else 'insufficient_evidence'
        change = direction if direction in {'emerging', 'transforming'} else 'transforming' if direction in {'growing', 'declining'} else None
        availability = 'reported_shortage' if title in {'Cybersecurity Analyst', 'Data Engineer', 'Forward Deployed Engineer'} else None
        dimensions = {'demand': demand, 'change': change, 'availability': availability}
        tags = {value for value in dimensions.values() if value}
        rows.append({'role_id': f'synthetic:{index}', 'title': title, 'synthetic': True,
                     'category': direction, 'categories': sorted(tags), 'dimensions': dimensions,
                     'tasks': tasks, 'skills': skills, 'baselines': BASELINES,
                     'assumption': 'Illustrative scenario - not an observed labour-market forecast. All classifications, tasks and skills are synthetic assumptions.',
                     'market': 'Global illustrative context'})
    categories = ['growing', 'declining', 'stable', 'emerging', 'transforming', 'reported_shortage', 'insufficient_evidence']
    counts = {c: sum(c in r['categories'] for r in rows) for c in categories}
    filtered = [r for r in rows if category == 'all' or category in r['categories']]
    return {'items': filtered[offset:offset+limit], 'total': len(filtered), 'offset': offset, 'limit': limit,
            'counts': counts, 'covered_roles': len(rows), 'catalogue_roles': len(SCENARIOS), 'sources': [],
            'method': 'Bundled synthetic scenarios, inspired by published jobs-outlook context. All markets include the same global illustrative scenarios, not local forecasts. Counts are scenario counts; a career can appear in multiple categories. Reported shortage means simulated shortage. Insufficient evidence demonstrates an intentionally unspecified demand outlook.'}
