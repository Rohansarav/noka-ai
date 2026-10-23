"""Deterministic scenario planning, private pathways and grounded impact."""
import json
import math
import copy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from backend.app.evidence_api import get_session
from backend.app.profile_security import active_session, same_origin
from backend.app.models import FutureWorkspace, Profile, ProfileSkill, Role, RoleSkill, Skill, SDGLink, SDGTarget, Source, IntelligenceRecord
from backend.app.matching import match_profile, prioritize_gaps, select_directions, confirmed_context
from backend.app.occupation_catalogue import occupation_evidence
from backend.app.pathway_exercises import exercise

router = APIRouter(prefix="/api", tags=["Future workspace"])
SCENARIOS = {
    "acceleration": {"name": "AI Acceleration", "assumption": "Rapid automation increases emphasis on designing, programming and evaluating systems.", "skills": ["Programming", "Technology Design", "Systems Analysis"]},
    "governed": {"name": "Governed AI", "assumption": "Stronger accountability increases emphasis on monitoring, quality and judgment.", "skills": ["Monitoring", "Quality Control Analysis", "Judgment and Decision Making"]},
    "collaboration": {"name": "Human-AI Collaboration", "assumption": "Augmentation increases emphasis on communication, learning and collaborative judgment.", "skills": ["Active Learning", "Coordination", "Critical Thinking", "Active Listening"]},
}
VERSION = "connected-planning-2026-10-21-v4"


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["acceleration", "governed", "collaboration"] | None = None
    role_id: str | None = Field(default=None, max_length=80)
    weekly_hours: int | None = Field(default=None, ge=1, le=40)


class Progress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_id: str = Field(max_length=40)
    status: Literal["planned", "in_progress", "completed"] | None = None
    note: str | None = Field(default=None, max_length=1000)


PRACTICE = {
    "Programming": ("Build a small data or workflow utility; add input checks and tests.", "Publish a runnable utility with a README, test cases and an explanation of limitations."),
    "Critical Thinking": ("Compare competing explanations for a work problem, checking each assumption against evidence.", "Write a decision memo with sources, counterarguments and a clearly justified recommendation."),
    "Judgment and Decision Making": ("Compare three options using stated criteria, consequences and uncertainty.", "Create a decision matrix and document what evidence would change your choice."),
    "Reading Comprehension": ("Read an occupational document, identify its main claims and explain them in your own words.", "Annotate a technical brief and produce a checked summary with references to the original."),
    "Active Listening": ("Practise an interview, paraphrase the speaker's needs and ask clarifying questions.", "Create an anonymised requirements brief and validate it against the interview notes."),
    "Active Learning": ("Choose an unfamiliar technique, practise it and compare the result with a worked example.", "Keep an experiment log showing feedback, corrections and one independent application."),
    "Writing": ("Draft a clear brief for a specific audience, then revise it using peer feedback.", "Produce a before-and-after communication sample explaining your revision decisions."),
    "Mathematics": ("Solve a relevant quantitative problem and check units, assumptions and sensitivity.", "Create a reproducible calculation notebook with worked examples and error checks."),
    "Systems Analysis": ("Map a workflow, identify inputs, constraints and likely failure points.", "Deliver a system map with a tested improvement and an explanation of trade-offs."),
    "Quality Control Analysis": ("Define acceptance criteria, design a representative sample and inspect defects.", "Produce a quality checklist and test report explaining corrective actions."),
    "Monitoring": ("Define useful process indicators and practise detecting a deviation from expected behaviour.", "Build an observation log with thresholds, anomalies and a response plan."),
    "Coordination": ("Break a collaborative task into owners, handoffs and dependencies.", "Create and run a small delivery plan, then reflect on missed handoffs and improvements."),
    "Speaking": ("Explain a technical idea in three minutes and refine it after audience feedback.", "Record a short role-relevant presentation and include the feedback and revised outline."),
    "Instructing": ("Teach a small practical task, assess understanding and adapt the explanation.", "Create a lesson, exercise and assessment rubric with evidence of feedback."),
}


def private(request, db, lock=False):
    owner = active_session(request, db)
    profile = db.scalar(select(Profile).where(Profile.session_hash == owner.token_hash)) if owner else None
    if not profile:
        raise HTTPException(404)
    statement=select(FutureWorkspace).where(FutureWorkspace.profile_id==profile.id)
    workspace=db.scalar(statement.with_for_update().execution_options(populate_existing=True)) if lock else db.get(FutureWorkspace,profile.id)
    if not workspace:
        workspace = FutureWorkspace(profile_id=profile.id, scenario="collaboration", weekly_hours=6,
                                    progress={}, conversation=[], updated_at=datetime.now(timezone.utc))
        db.add(workspace)
        db.commit()
    return profile, workspace


def ranked(profile, db, scenario, base=None, requirements=None, selected_role=None):
    """Preserve skill-fit scores; expose scenario emphasis as a separate planning index."""
    matches = copy.deepcopy(base if base is not None else match_profile(profile, db, limit=None)["matches"])
    if requirements is None:
        requirements = occupation_evidence(db)[1]
    names = SCENARIOS[scenario]["skills"]
    grouped = {}
    for link, skill in requirements:
        if skill.canonical_name in names:
            grouped.setdefault(link.role_id, []).append((link, skill))
    for match in matches:
        relevant = grouped.get(match['role_id'], [])
        emphasis = sum(max(0, link.required_importance-3) for link, _ in relevant)
        match["scenario_emphasis"] = round(emphasis, 2)
        match["context_emphasis"] = round(5*match.get('context_alignment', 0), 2)
        match["planning_index"] = round(match["score"]+emphasis+match['context_emphasis'], 2)
        match["scenario_reason"] = SCENARIOS[scenario]["assumption"]
        match["priority_skills"] = [skill.canonical_name for link, skill in relevant if link.required_importance > 3]
    ordered = sorted(matches, key=lambda m: (-m.get('technical',{}).get('matched_count',0),-m['planning_index'], m['title']))
    visible = select_directions(ordered)
    if selected_role and selected_role not in {m['role_id'] for m in visible}:
        # Preserve a user's explored career without presenting it as a recommendation.
        visible.extend({**m, 'is_explored': True} for m in ordered if m['role_id'] == selected_role)
    return visible


def pathway(profile, workspace, db, matches):
    match = next((m for m in matches if m["role_id"] == workspace.role_id), None)
    if not match:
        return []
    role = db.get(Role, workspace.role_id)
    priority = SCENARIOS[workspace.scenario]["skills"]
    gaps = prioritize_gaps(match['gaps'], priority)
    # A focused project is actionable; retain started work when the lens changes.
    retained = {g['skill_id'] for g in gaps if workspace.progress.get(f"{workspace.role_id}:{g['skill_id']}", 'planned') != 'planned'}
    unfinished = [g for g in gaps if workspace.progress.get(f"{workspace.role_id}:{g['skill_id']}", 'planned') != 'completed']
    focus = {g['skill_id'] for g in unfinished[:5]} | retained
    gaps = [g for g in gaps if g['skill_id'] in focus]
    tasks, hours = [], 0
    for gap in gaps:
        key = f"{workspace.role_id}:{gap['skill_id']}"
        status = workspace.progress.get(key, "planned")
        activity,project=PRACTICE.get(gap["name"], (f"Choose a realistic {match['title']} task requiring {gap['name'].lower()}, practise it and ask an experienced peer to review the result.", f"Document a {gap['name'].lower()} case study with your approach, a work sample, feedback and a revised result."))
        unassessed = gap.get('development') == 'missing'
        effort = 4 if unassessed else max(4, math.ceil(16*gap["gap"]))
        start = math.floor(hours/workspace.weekly_hours)+1
        if status != "completed":
            hours += effort
        previous = tasks[-1] if tasks else None
        handoff = f"Use the {previous['name'].lower()} work sample from step {len(tasks)} as input; explain how this step improves the same case study." if previous else f"Choose one small case study based on this occupation's work: {role.description if role else match['title']}. Define an audience, a practical problem, success criteria and a scope you can finish within your weekly commitment."
        tasks.append({**gap, "planning_priority":round(gap['priority']*(1.25 if gap['name'] in priority else 1),4), "status": status, "effort_hours": effort, "start_week": start,
                      "end_week": max(start, math.ceil(hours/workspace.weekly_hours)), "scenario_priority": gap["name"] in priority,
                      "objective": f"{'Check your current ability in' if unassessed else 'Strengthen'} {gap['name'].lower()} within your {match['title']} case study.",
                      "activity": activity,
                      "project": project + ' Add this evidence to the same career portfolio.',
                      "note": workspace.progress.get("note:"+key,""),
                      "dependencies": [previous['skill_id']] if previous else [],
                      "handoff": handoff, "assessment_needed":unassessed,
                      "acceptance_criteria":[f"Include a concrete {gap['name'].lower()} work sample relevant to {match['title']}.", 'Check the result against your case study success criteria and record feedback or a test.', 'Save an evidence link or reflection describing what worked, limitations and the next improvement.'],
                      **exercise(gap["name"], match["title"], activity, project),
                      "why": f"Published importance {gap['importance']}/5. " + ('No self-rating recorded: validate before committing to more study.' if unassessed else f"Self-rated proficiency leaves a {gap['gap']:.0%} development gap.") + (" Scenario focus applies a 1.25× planning weight." if gap['name'] in priority else " Standard 1× planning weight."),
                      "estimate_method": "Timebox: 4 hours for an unassessed skill check; otherwise 16 × self-rated gap, minimum 4 hours. Sequential portfolio handoffs are a suggested workflow, not occupational prerequisites or a promise of mastery."})
    return tasks


def snapshot(profile, workspace, db):
    base = match_profile(profile, db, limit=None)["matches"]
    requirements = occupation_evidence(db)[1]
    comparisons = {s: ranked(profile,db,s,base,requirements,workspace.role_id) for s in SCENARIOS}
    matches = comparisons[workspace.scenario]
    selected = next((m for m in matches if m["role_id"] == workspace.role_id), None)
    strengths = [s.canonical_name for p,s in db.execute(select(ProfileSkill,Skill).join(Skill).where(ProfileSkill.profile_id==profile.id)).all() if p.level in {"strong","working"}]
    worlds={}
    for scenario in SCENARIOS:
        preview=SimpleNamespace(scenario=scenario,role_id=workspace.role_id,weekly_hours=workspace.weekly_hours,progress=workspace.progress)
        tasks=pathway(profile,preview,db,comparisons[scenario])
        story=None
        if selected:
            story=f"Imagine it is 2030. In the {SCENARIOS[scenario]['name']} scenario, you could work toward {selected['title']}. Your confirmed strengths include {', '.join(strengths[:3]) or 'skills you are beginning to learn'}. Prioritise {', '.join(t['name'] for t in tasks[:3]) or 'continued practical experience'}. This is a possible direction, not an employment prediction."
        worlds[scenario]={"pathway":tasks,"future_self":story}
    return {"profile_id": profile.id, "profile_revision": profile.updated_at.isoformat(), "scenario": workspace.scenario,
            "role_id": workspace.role_id, "weekly_hours": workspace.weekly_hours, "version": VERSION,
            "scenarios": SCENARIOS, "matches": matches, "pathway": pathway(profile,workspace,db,matches),
            "future_self": worlds[workspace.scenario]["future_self"], "conversation": workspace.conversation, "worlds":worlds,
            "comparisons": comparisons,
            "analysis_context": confirmed_context(profile),
            "pathway_scope": {"total_development_areas":len(selected['gaps']) if selected else 0,"focus_limit":5,"project_title":f"{selected['title']} career portfolio" if selected else None},
            "method": "Discover related occupations using shared occupation families and requirements or multiple confirmed occupational skills/software connections; rank relevance separately from coverage. Software adds no coverage points. Planning index = documented coverage + 5 × lexical context alignment + scenario emphasis. Retain all confirmed targets plus up to five supported discoveries. Scenario emphasis is sum(max(0, importance − 3)) for named scenario skills, not a forecast. Graph and pathway share importance × gap × 1.25 for scenario focus skills, otherwise × 1. A focused pathway selects five areas and retains started work. Unrecorded skills begin with a validation task, not an assumption of inability."}


@router.get("/profiles/current/future")
def get_future(request: Request, response: Response, db: Session=Depends(get_session)):
    response.headers["Cache-Control"]="no-store"
    profile, workspace = private(request,db)
    return snapshot(profile,workspace,db)


@router.put("/profiles/current/future", dependencies=[Depends(same_origin)])
def save_future(body: Preferences, request: Request, response: Response, db: Session=Depends(get_session)):
    response.headers["Cache-Control"]="no-store"
    profile,workspace = private(request,db,lock=True)
    if body.role_id and body.role_id not in {m['role_id'] for m in match_profile(profile,db,limit=None)['matches']}:
        raise HTTPException(422)
    for key,value in body.model_dump(exclude_none=True).items():
        setattr(workspace,key,value)
    workspace.updated_at=datetime.now(timezone.utc)
    db.commit()
    return snapshot(profile,workspace,db)


@router.put("/profiles/current/pathway", dependencies=[Depends(same_origin)])
def save_progress(body: Progress, request: Request, response: Response, db: Session=Depends(get_session)):
    response.headers["Cache-Control"]="no-store"
    profile,workspace=private(request,db,lock=True)
    tasks=pathway(profile,workspace,db,ranked(profile,db,workspace.scenario,selected_role=workspace.role_id))
    if body.skill_id not in {t["skill_id"] for t in tasks}:
        raise HTTPException(422)
    if body.status is None and body.note is None:
        raise HTTPException(422)
    evidence = body.note if body.note is not None else workspace.progress.get(f"note:{workspace.role_id}:{body.skill_id}", '')
    if body.status == 'completed' and len(evidence.strip()) < 20:
        raise HTTPException(422, detail='Save at least 20 characters of evidence or reflection before completing a milestone.')
    if body.status is not None:
        workspace.progress={**workspace.progress, f"{workspace.role_id}:{body.skill_id}":body.status}
    if body.note is not None:
        from backend.app.skill_extraction import clean_text
        workspace.progress={**workspace.progress, f"note:{workspace.role_id}:{body.skill_id}":clean_text(body.note)}
    workspace.updated_at=datetime.now(timezone.utc)
    db.commit()
    return snapshot(profile,workspace,db)


@router.get("/impact/{role_id}")
def impact(role_id: str, db: Session=Depends(get_session)):
    role=db.get(Role,role_id)
    if not role: raise HTTPException(404)
    # Match the Career Universe's context threshold; readiness still uses 3/5.
    skills=dict(db.execute(select(Skill.id,Skill.canonical_name).join(RoleSkill).where(RoleSkill.role_id==role_id,RoleSkill.required_importance>=2)).all())
    links=db.scalars(select(SDGLink).where(or_(SDGLink.role_id==role_id,SDGLink.skill_id.in_(skills)))).all()
    results=[]
    for link in links:
        target=db.get(SDGTarget,link.target_id)
        source=db.get(Source,link.source_id)
        approved=link.curation_status=="human_reviewed" and bool(link.reviewed_by and link.reviewed_at)
        results.append({"id":link.id,"role":role.title,"skill":skills.get(link.skill_id),
                        "responsibility":role.description if link.role_id else None,
                        "target_id":target.id,"goal_id":target.goal_id,"target":target.description,
                        "explanation":link.rationale,"status":"Curated SDG relationship" if approved else "Pending review",
                        "url":source.canonical_url,"relationship_type":"role responsibility" if link.role_id else "published skill context"})
    return {"role":role.title,"relationships":results,"limitation":"Potential contribution, not measured impact. Skill relevance does not establish every role's contribution."}


@router.get("/forecasts")
def forecasts():
    path=Path(__file__).resolve().parents[2]/"ml/artifacts/evaluation.json"
    if not path.exists():
        return {"status":"unavailable","message":"No evaluated artifact is available."}
    return {"status":"evaluated",**json.loads(path.read_text(encoding="utf-8"))}


@router.get("/intelligence")
def intelligence(db: Session=Depends(get_session)):
    # Bound each kind separately so many refresh runs cannot evict every outlook.
    records=[]
    for kind,limit in (("context",10),("finding",60),("scout_run",10),("outlook",100)):
        records.extend(db.scalars(select(IntelligenceRecord).where(IntelligenceRecord.kind==kind).order_by(IntelligenceRecord.created_at.desc()).limit(limit)))
    successful_record=db.scalar(select(IntelligenceRecord).where(IntelligenceRecord.kind=="scout_run", IntelligenceRecord.payload["status"].as_string()=="succeeded").order_by(IntelligenceRecord.created_at.desc()).limit(1))
    successful=successful_record.payload if successful_record else None
    return {"market":"Malaysia first; international context is labelled",
            "last_successful_run":successful,
            "findings":sorted({r.payload['url']:r.payload for r in reversed(records) if r.kind in {"finding","context"}}.values(), key=lambda p:p.get("evidence_type")!="Source-checked context"),
            "runs":[r.payload for r in records if r.kind=="scout_run"][:10],
            "outlooks":[r.payload for r in records if r.kind=="outlook"],
            "method":"Unreviewed research is not employment-demand evidence. Exact canonical name matches are discovery links only. Without reviewed directional evidence, outlook is insufficient evidence."}
