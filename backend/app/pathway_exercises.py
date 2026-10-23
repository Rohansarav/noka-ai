"""Suggested portfolio exercises, not verified occupational prerequisites."""

DELIVERABLES = {
    'Programming': 'A runnable utility: include setup instructions, sample inputs and outputs, input validation, and tests for a normal case and a failure case.',
    'Critical Thinking': 'A decision memo: state the problem, compare two explanations, cite supporting and contradicting evidence, and justify a recommendation with its limitations.',
    'Judgment and Decision Making': 'A decision matrix: compare three options, define criteria and weights, explain trade-offs, and identify evidence that would change the choice.',
    'Reading Comprehension': 'An annotated document and one-page brief: link the original, identify three main claims, point to supporting passages, explain implications for your case study, and flag one ambiguity.',
    'Active Listening': 'An anonymised requirements brief: include interview questions, paraphrased needs, clarifying questions, and corrections made after checking your understanding.',
    'Active Learning': 'An experiment notebook: record the technique and source, your first attempt, feedback, revisions, and an independent application to the case study.',
    'Writing': 'A before-and-after brief: identify the audience and purpose, include the original and revised versions, and explain three edits made after feedback.',
    'Mathematics': 'A reproducible calculation sheet: include inputs, units, formulas, a worked example, an independent check, and sensitivity to a changed assumption.',
    'Systems Analysis': 'A workflow map and improvement note: label inputs, outputs, dependencies and failure points; compare the original and proposed workflow and explain a trade-off.',
    'Quality Control Analysis': 'A quality test report: define acceptance criteria, sample selection and test cases; record defects, corrective actions and retest results.',
    'Monitoring': 'A monitoring report: include an indicator table, thresholds and their rationale, normal and abnormal observations, a screenshot or log excerpt, a response plan, and one limitation. Label simulated observations.',
    'Coordination': 'A delivery plan and retrospective: name responsibilities, handoffs and dependencies; record a missed or simulated handoff and explain how you would improve it.',
    'Speaking': 'A three-minute presentation and revision note: state the audience, show the case-study problem and recommendation, record feedback, and explain how you revised the presentation.',
    'Instructing': 'A mini lesson pack: include a learning objective, demonstration, learner exercise, assessment rubric, and changes made after checking understanding.',
}


def exercise(name, role_title, activity, project):
    """Keep each exercise attached to the chosen career and the same portfolio."""
    steps = [f'Choose a small {role_title} case-study task where {name.lower()} matters. Define the intended result.',
             activity,
             'Check your result against the intended outcome. Record feedback or a test and explain one improvement.']
    checks = ['Include the work sample and supporting observations described in your deliverable.',
              f'Explain how your {name.lower()} work informs the next decision in the case study.',
              'Record a check or feedback, one limitation, and your next improvement.']
    if name == 'Monitoring':
        steps = ['Choose a small process or system you can safely observe in your case study.',
                 'Select three indicators. For a software system, examples are response time, failed requests and availability; adapt them to your case study.',
                 'Set a threshold for each indicator and explain the rationale.',
                 'Compare normal observations with a safely controlled abnormal condition or clearly labelled simulated observations.',
                 'Record the deviation, propose a response, and explain how you would check recovery.']
        checks = ['Document three indicators and explain their thresholds.', 'Include normal and abnormal observations; label any simulation.', 'Explain a response, recovery check and limitation.']
    elif name == 'Reading Comprehension':
        steps = [f'Choose a technical specification, guidance document or occupational report relevant to your {role_title} case study. Record its source.',
                 'Identify three main claims or requirements and annotate the passages supporting them.',
                 'Explain each in your own words and distinguish stated facts from your interpretation.',
                 'Write how the document affects your case-study decisions and flag an ambiguity to clarify.']
        checks = ['Link the original document and annotate three supporting passages.', 'Separate the source claims from your interpretation.', 'Explain a case-study implication and one unresolved question.']
    return {'task_steps': steps, 'project': DELIVERABLES.get(name, project + ' Include your approach, a work sample, a check or feedback, revisions and limitations.'), 'acceptance_criteria': checks}
