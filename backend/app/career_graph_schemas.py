"""Read-only universe contracts. Gap attributes belong to role edges, never universal skill claims."""
from datetime import datetime
from typing import Literal
from pydantic import Field
from backend.app.profile_schemas import Contract
from backend.app.schemas import SourceOut

MAX_NODES = 88
MAX_EDGES = 300
NodeType = Literal["profile", "owned_skill", "required_skill", "role", "sdg", "sdg_target"]
EdgeType = Literal["has_skill", "requires_skill", "missing_skill", "contributes_to_target", "target_belongs_to_goal"]


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


class CareerGraph(Contract):
    status: Literal["no_profile", "insufficient_profile_information", "ready"]
    profile_revision: str | None
    generated_at: datetime
    nodes: list[CareerNode] = Field(max_length=MAX_NODES)
    edges: list[CareerEdge] = Field(max_length=MAX_EDGES)
    sources: list[SourceOut]
    methodology: str
    limitations: list[str]
