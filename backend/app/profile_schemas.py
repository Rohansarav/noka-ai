"""Strict private contracts: resumes and contact details never become profile fields."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class AnalysisInput(Contract):
    """The same text contract follows protected document parsing or manual entry."""
    text: str = Field(min_length=20, max_length=20000)


class ConfirmedSkill(Contract):
    skill_id: str = Field(max_length=40)
    level: Literal["learning", "working", "strong"] = "working"
    years: float | None = Field(default=None, ge=0, le=60)


class CareerAspiration(Contract):
    title: str = Field(min_length=2, max_length=120)
    role_ids: list[str] = Field(default_factory=list, max_length=3)
    status: Literal['confirmed', 'unmapped'] = 'unmapped'

    @model_validator(mode='after')
    def consistent(self):
        self.title = self.title.strip()
        if len(self.title) < 2 or len(set(self.role_ids)) != len(self.role_ids) or (self.status == 'confirmed') != bool(self.role_ids):
            raise ValueError('Confirm a catalogue interpretation, or keep the aspiration unmapped.')
        return self


class OnboardingDraft(Contract):
    step: int = Field(default=0, ge=0, le=2)
    status: Literal["student", "employed", "self_employed", "seeking", "other"] = "student"
    current_field: str = Field(default="", max_length=160)
    experience_years: float = Field(default=0, ge=0, le=60)
    country: Literal["MY", "US", "SG", "GB", "AU", "OTHER"] = "MY"
    market: Literal["MY", "US", "SG", "GB", "AU", "OTHER"] = "MY"
    goal: str = Field(default="", max_length=400)
    projects: str = Field(default="", max_length=2000)
    constraints: str = Field(default="", max_length=600)
    aspirations: list[CareerAspiration] = Field(default_factory=list, max_length=5)
    interests: list[str] = Field(default_factory=list, max_length=5)
    weekly_hours: int = Field(default=6, ge=1, le=40)
    skills: list[ConfirmedSkill] = Field(default_factory=list, max_length=60)


class SaveSkills(Contract):
    skills: list[ConfirmedSkill] = Field(max_length=60)
    country: Literal["MY", "US", "SG", "GB", "AU", "OTHER"] = "MY"
    interests: list[str] = Field(default_factory=list, max_length=5)
    onboarding: OnboardingDraft | None = None


class ProfileView(Contract):
    id: str
    country: str
    interests: list[str]
    is_demo: bool
    confirmed: bool
    updated_at: str
    skills: list[ConfirmedSkill]
    onboarding: dict | None = None


class CurrentProfile(Contract):
    profile: ProfileView | None


class Candidate(Contract):
    mention: str
    years: float | None
    evidence_excerpt: str
    confidence: Literal["low", "medium", "high"]
    mapping: Literal["exact", "alias", "fuzzy", "ambiguous", "unmapped", "reasoned"]
    options: list[str]
    mentions: list[str] = Field(default_factory=list)


class ExtractionResponse(Contract):
    candidates: list[Candidate]
    mode: Literal["openai", "local", "manual_fallback"]
    message: str
    truncated: bool
    warnings: list[str] = Field(default_factory=list)
    duplicates_merged: int = 0
    schema_version: Literal["skill-review-v2"] = "skill-review-v2"


class Gap(Contract):
    skill_id: str
    name: str
    importance: float
    gap: float
    critical: bool
    priority: float = 0
    development: Literal['missing', 'developing'] = 'missing'


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
    is_target: bool = False
    context_alignment: float = 0
    context_reasons: list[str] = Field(default_factory=list)
    selection_reason: str = ''
    gap_method: str = 'importance × remaining proficiency gap; scenario emphasis breaks ties'


class MatchesResponse(Contract):
    status: Literal["ready", "insufficient_profile_information"]
    matches: list[Match]
    methodology: str
    geography_note: str
