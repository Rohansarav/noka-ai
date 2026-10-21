"""Read-only universe contracts. Gap attributes belong to role edges, never universal skill claims."""
from datetime import datetime
from typing import Literal
from pydantic import Field
from backend.app.profile_schemas import Contract, TechnicalAlignment, ReadinessAssessment
from backend.app.schemas import SourceOut

MAX_NODES = 170
MAX_EDGES = 2000
NodeType = Literal["profile", "owned_skill", "required_skill", "context_skill", "technology", "role", "sdg", "sdg_target"]
EdgeType = Literal["has_skill", "requires_skill", "context_requirement", "missing_skill", "uses_technology", "contributes_to_target", "target_belongs_to_goal"]


class CareerNode(Contract):
    id: str
    type: NodeType
    entity_id: str
    label: str
    description: str = ""
    source_ids: list[str] = Field(default_factory=list)
    review_status: str | None = None
    level: Literal["learning", "working", "strong"] | None = None
    years: float | None = None
    skill_count: int | None = None
    country: str | None = None
    is_demo: bool = False
    score: float | None = Field(default=None, ge=0, le=100)
    coverage: float | None = Field(default=None, ge=0, le=100)
    explanation: str | None = None
    goal_id: int | None = None
    is_target: bool = False
    context_reasons: list[str] = Field(default_factory=list)
    selection_reason: str = ''
    category: str | None = None
    technical: TechnicalAlignment | None = None
    readiness_status: Literal['self_reported','not_assessed'] = 'self_reported'
    assessment: ReadinessAssessment | None = None


class CareerEdge(Contract):
    id: str
    type: EdgeType
    source: str
    target: str
    source_ids: list[str] = Field(default_factory=list)
    importance: float | None = Field(default=None, ge=1, le=5)
    gap: float | None = Field(default=None, ge=0, le=1)
    critical: bool = False
    review_status: str | None = None
    rationale: str | None = None
    supporting_id: str | None = None


class ImpactAvailability(Contract):
    reviewed_links: int = 0
    pending_links: int = 0
    message: str = 'No reviewed SDG relationship is recorded for these displayed careers and skills. This is missing evidence, not proof of no impact.'


class CareerGraph(Contract):
    status: Literal["no_profile", "insufficient_profile_information", "ready"]
    profile_revision: str | None
    generated_at: datetime
    nodes: list[CareerNode] = Field(max_length=MAX_NODES)
    edges: list[CareerEdge] = Field(max_length=MAX_EDGES)
    sources: list[SourceOut]
    methodology: str
    limitations: list[str]
    impact: ImpactAvailability = Field(default_factory=ImpactAvailability)
