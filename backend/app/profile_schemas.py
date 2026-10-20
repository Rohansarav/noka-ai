"""Strict private contracts: resumes and contact details never become profile fields."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateProfile(Contract):
    is_demo: bool = False


class SkillMention(Contract):
    mention: str = Field(max_length=120)
    years: float | None = Field(ge=0, le=60)
    evidence_excerpt: str = Field(max_length=300)
    confidence: Literal["low", "medium", "high"]


class ExtractedSkills(Contract):
    skills: list[SkillMention] = Field(max_length=60)


class ConfirmedSkill(Contract):
    skill_id: str = Field(max_length=40)
    level: Literal["learning", "working", "strong"] = "working"
    years: float | None = Field(default=None, ge=0, le=60)


class SaveSkills(Contract):
    skills: list[ConfirmedSkill] = Field(max_length=60)
    country: Literal["MY", "US", "SG", "GB", "AU", "OTHER"] = "MY"
    interests: list[str] = Field(default_factory=list, max_length=5)


class ProfileView(Contract):
    id: str
    country: str
    interests: list[str]
    is_demo: bool
    confirmed: bool
    updated_at: str
    skills: list[ConfirmedSkill]


class CurrentProfile(Contract):
    profile: ProfileView | None


class Candidate(Contract):
    mention: str
    years: float | None
    evidence_excerpt: str
    confidence: Literal["low", "medium", "high"]
    mapping: Literal["exact", "alias", "fuzzy", "ambiguous", "unmapped"]
    options: list[str]


class ExtractionResponse(Contract):
    candidates: list[Candidate]
    mode: Literal["openai", "local", "manual_fallback"]
    message: str
    truncated: bool


class Gap(Contract):
    skill_id: str
    name: str
    importance: float
    gap: float
    critical: bool


class Match(Contract):
    role_id: str
    title: str
    score: float
    coverage: float
    transferable_coverage: float
    interest_adjustment: float
    gaps: list[Gap]
    explanation: str
    source_ids: list[str]


class MatchesResponse(Contract):
    status: Literal["ready", "insufficient_profile_information"]
    matches: list[Match]
    methodology: str
    geography_note: str
