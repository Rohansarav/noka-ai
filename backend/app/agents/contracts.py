from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StartExecution(Contract):
    agent: Literal["matchmaker"] = "matchmaker"
    question: str = Field(min_length=3, max_length=1000)
    role_id: str = Field(min_length=1, max_length=40)
    node_id: str | None = Field(default=None, max_length=120)


class EmptyArgs(Contract):
    pass


class RoleArgs(Contract):
    role_id: str = Field(min_length=1, max_length=40)


class Selection(Contract):
    # The model selects evidence, never authors numerical scores or unsupported prose.
    sections: list[Literal["fit", "requirements", "gaps", "evidence", "sdgs", "scenario", "pathway", "forecast", "signals"]] = Field(min_length=1, max_length=9)
    focus_role: str
    highlight_skills: list[str] = Field(max_length=12)
    open_evidence: str | None


class EventPayload(Contract):
    tool: Literal["get_current_profile", "get_confirmed_skills", "get_ranked_matches", "get_role_requirements", "get_skill_gaps", "get_role_evidence", "get_reviewed_sdg_connections", "get_future_context", "get_forecast_context", "get_scout_findings"] | None = None
    related_entity: str | None = Field(default=None, max_length=64)
    stage: Literal["preparing", "provider_request", "provider_response", "tool_execution", "result_validation"] | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    provider_code: Literal["invalid_json_schema", "invalid_function_parameters", "unsupported_parameter", "model_not_found", "insufficient_quota", "invalid_api_key", "rate_limit_exceeded", "permission_denied", "other"] | None = None
    error_type: Literal["AttributeError", "TypeError", "ValueError", "ValidationError", "provider", "other"] | None = None
    reason: Literal["unauthorized_tool", "invalid_reference", "parallel_calls_rejected", "unsupported_result", "unsupported_highlight"] | None = None
