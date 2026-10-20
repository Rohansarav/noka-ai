"""Only allowlisted categories leave the exception boundary; never exception messages/bodies."""
from openai import APIStatusError, APIConnectionError, APITimeoutError
from pydantic import ValidationError
from typing import Any

PROVIDER_CODES = {"invalid_json_schema", "invalid_function_parameters", "unsupported_parameter", "model_not_found", "insufficient_quota", "invalid_api_key", "rate_limit_exceeded", "permission_denied"}


def failure_details(exc: Exception, stage: str):
    """Preserve actionable status/category without user text, credentials or provider prose."""
    payload: dict[str, Any] = {"stage": stage}
    if isinstance(exc, (APITimeoutError, TimeoutError)):
        return "timeout", {**payload, "error_type": "provider"}
    if isinstance(exc, APIStatusError):
        raw_code = exc.code
        payload.update(http_status=exc.status_code, provider_code=raw_code if isinstance(raw_code, str) and raw_code in PROVIDER_CODES else "other", error_type="provider")
        status = exc.status_code
        code = {400:"provider_request_rejected",401:"provider_authentication_error",403:"provider_permission_error",404:"provider_model_unavailable"}.get(status, "provider_unavailable")
        if status == 429: code = "provider_quota_exceeded" if raw_code == "insufficient_quota" else "provider_rate_limited"
        return code, payload
    if isinstance(exc, APIConnectionError):
        return "provider_connection_error", {**payload, "error_type":"provider"}
    if isinstance(exc, ValidationError):
        return "tool_arguments_invalid" if stage == "tool_execution" else "result_validation_error", {**payload,"error_type":"ValidationError"}
    allowed_runtime = {"ai_unavailable", "timeout", "profile_changed", "tool_limit", "turn_limit"}
    if type(exc) is RuntimeError and str(exc) in allowed_runtime:
        return str(exc), payload
    if type(exc) is ValueError and str(exc) in {"unauthorized_tool", "invalid_reference", "parallel_calls_rejected", "unsupported_result", "unsupported_highlight"}:
        return "execution_validation_error", {**payload, "error_type":"ValueError", "reason":str(exc)}
    safe_type = type(exc).__name__ if type(exc) in {AttributeError, TypeError, ValueError} else "other"
    return "provider_or_validation_error", {**payload, "error_type":safe_type}
