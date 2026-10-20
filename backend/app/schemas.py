"""Strict public API contracts, mirrored in frontend/src/evidence-api.ts."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SourceOut(Contract):
    id: str
    dataset: str
    title: str
    canonical_url: str
    file_url: str
    publisher: str
    publication_date: date | None
    retrieved_at: datetime
    version: str
    sha256: str
    license: str
    license_url: str
    geography: str
    granularity: str
    notes: str


class RoleOut(Contract):
    id: str
    title: str
    description: str
    occupation_code: str
    country: str
    sector: str | None
    evidence_status: Literal["sector_proxy_only", "not_covered"]
    crosswalk_rationale: str
    curation_status: str
    source_id: str
    individual_statistically_forecastable: Literal[False] = False


class SkillOut(Contract):
    id: str
    canonical_name: str
    aliases: list[str]
    category: str
    source_id: str


class RoleSkillOut(Contract):
    skill: SkillOut
    required_importance: float
    scale: Literal["O*NET IM 1–5"] = "O*NET IM 1–5"
    source_id: str


class SDGLinkOut(Contract):
    target_id: str
    role_id: str | None
    skill_id: str | None
    entity_name: str
    rationale: str
    source_id: str
    curation_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None


class RoleDetail(RoleOut):
    source: SourceOut
    skills: list[RoleSkillOut]
    sdg_links: list[SDGLinkOut]


class RolesResponse(Contract):
    roles: list[RoleOut]


class SkillsResponse(Contract):
    skills: list[SkillOut]


class SectorSummary(Contract):
    country: str
    sector: str
    observation_count: int
    start_date: date
    end_date: date


class RunOut(Contract):
    dataset: str
    started_at: datetime
    completed_at: datetime
    status: str
    row_count: int
    message: str


class DirectionOut(Contract):
    subject: str
    direction: str
    rationale: str
    horizon: str
    source_id: str
    curation_status: str


class SummaryResponse(Contract):
    database: Literal["postgresql", "sqlite"]
    counts: dict[str, int]
    countries: list[str]
    start_date: date | None
    end_date: date | None
    sectors: list[SectorSummary]
    sources: list[SourceOut]
    last_successful_imports: list[RunOut]
    last_attempt: RunOut | None
    structural_directions: list[DirectionOut]
    limitations: list[str]


class ObservationOut(Contract):
    date: date
    indexed_value: float
    adjusted_flag: bool
    source_id: str


class HistoryResponse(Contract):
    country: Literal["US"] = "US"
    sector: str
    granularity: Literal["occupational sector"] = "occupational sector"
    variable: Literal["total postings"] = "total postings"
    frequency: Literal["daily"] = "daily"
    baseline: Literal["2020-02-01 = 100"] = "2020-02-01 = 100"
    points: list[ObservationOut]
    sources: list[SourceOut]


class TargetOut(Contract):
    id: str
    goal_id: int
    description: str
    source_id: str
    links: list[SDGLinkOut]


class SDGOut(Contract):
    id: int
    title: str
    description: str
    source_id: str
    official_url: str
    targets: list[TargetOut]


class SDGsResponse(Contract):
    goals: list[SDGOut]
    sources: list[SourceOut]
