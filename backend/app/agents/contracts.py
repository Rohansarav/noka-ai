from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StartExecution(Contract):
    agent: Literal["matchmaker"] = "matchmaker"
    question: str = Field(min_length=3, max_length=1000)
    role_id: str = Field(min_length=1, max_length=40)


class EmptyArgs(Contract):
    pass


class RoleArgs(Contract):
    role_id: str = Field(min_length=1, max_length=40)


class Selection(Contract):
    # The model selects evidence, never authors numerical scores or unsupported prose.
    sections: list[Literal["fit", "requirements", "gaps", "evidence", "sdgs"]] = Field(min_length=1, max_length=5)
    focus_role: str
    highlight_skills: list[str] = Field(max_length=12)
    open_evidence: str | None


class EventPayload(Contract):
    tool: Literal["get_current_profile", "get_confirmed_skills", "get_ranked_matches", "get_role_requirements", "get_skill_gaps", "get_role_evidence", "get_reviewed_sdg_connections"] | None = None
    related_entity: str | None = Field(default=None, max_length=64)
