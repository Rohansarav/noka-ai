"""Bounded contracts for source-grounded, human-reviewed private planning."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class StartResearch(Strict):
    role_id: str = Field(min_length=1, max_length=80)
    description: str = Field(default='', max_length=16000)
    source_url: str = Field(default='', max_length=1000)


class RequirementDraft(Strict):
    source_id: str
    title: str = Field(min_length=3, max_length=180)
    quote: str = Field(min_length=12, max_length=700)
    priority: Literal['required', 'preferred', 'unspecified']


class PostingAssessment(Strict):
    source_id: str
    is_job: bool
    relevant: bool
    location: str = Field(max_length=160)
    availability: Literal['not_verified', 'explicitly_closed']
    reason: str = Field(max_length=400)


class Extraction(Strict):
    postings: list[PostingAssessment] = Field(max_length=6)
    requirements: list[RequirementDraft] = Field(max_length=18)


class ReviewItem(Strict):
    requirement_id: str = Field(max_length=40)
    starting_point: Literal['unassessed', 'learn', 'practice', 'demonstrate']


class ReviewResearch(Strict):
    items: list[ReviewItem] = Field(min_length=1, max_length=18)


class MilestoneDraft(Strict):
    title: str = Field(min_length=3, max_length=180)
    objective: str = Field(min_length=10, max_length=700)
    requirement_ids: list[str] = Field(min_length=1, max_length=18)
    steps: list[str] = Field(min_length=2, max_length=5)
    deliverable: str = Field(min_length=10, max_length=700)
    acceptance_criteria: list[str] = Field(min_length=2, max_length=4)
    learn: str = Field(min_length=10, max_length=700)
    effort_hours: int = Field(ge=1, le=40)


class ProjectDraft(Strict):
    title: str = Field(min_length=5, max_length=180)
    problem: str = Field(min_length=20, max_length=1000)
    audience: str = Field(min_length=5, max_length=300)
    why_you: str = Field(min_length=20, max_length=1000)
    scope: str = Field(min_length=20, max_length=1000)
    assumptions: list[str] = Field(min_length=1, max_length=6)
    milestones: list[MilestoneDraft] = Field(min_length=3, max_length=6)


class ProjectProgress(Strict):
    milestone_id: str = Field(max_length=40)
    note: str = Field(max_length=2000)
    status: Literal['planned', 'in_progress', 'completed']


class Activity(Strict):
    stage: str
    message: str
    at: str


class Posting(Strict):
    id: str
    title: str
    url: str | None
    origin: Literal['web', 'manual']
    retrieved_at: str
    location: str
    availability: str
    reason: str


class Requirement(RequirementDraft):
    id: str


class SavedMilestone(MilestoneDraft):
    id: str
    note: str
    status: Literal['planned', 'in_progress', 'completed']


class SavedProject(ProjectDraft):
    milestones: list[SavedMilestone]
    accepted_at: str | None = None
    accepted_by: str | None = None


class ReviewRecord(Strict):
    reviewed_at: str
    reviewed_by: str
    items: list[ReviewItem]


class ResearchView(Strict):
    id: str
    role_id: str
    target: str
    market: str
    status: Literal['queued', 'searching', 'extracting', 'analyzing', 'review', 'planning', 'ready', 'failed']
    created_at: str
    events: list[Activity]
    sources: list[Posting]
    requirements: list[Requirement]
    review: ReviewRecord | None
    project: SavedProject | None
    error: str | None
    evolution: dict | None = None
    update_history: list[dict] = Field(default_factory=list)


class ResearchHistory(Strict):
    runs: list[ResearchView]
