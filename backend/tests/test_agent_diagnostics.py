"""Safe error categories must never include provider messages, credentials or input."""
import json
import httpx
import pytest
from openai import BadRequestError, AuthenticationError, RateLimitError
from backend.app.agents.diagnostics import failure_details
from backend.app.agents.contracts import EventPayload


@pytest.mark.parametrize('exception,status,provider_code,expected',[
    (BadRequestError,400,'invalid_json_schema','provider_request_rejected'),
    (AuthenticationError,401,'invalid_api_key','provider_authentication_error'),
    (RateLimitError,429,'insufficient_quota','provider_quota_exceeded'),
    (RateLimitError,429,'rate_limit_exceeded','provider_rate_limited'),
])
def test_provider_failure_preserves_only_allowlisted_metadata(exception,status,provider_code,expected):
    response=httpx.Response(status,request=httpx.Request('POST','https://api.openai.com/v1/responses'))
    exc=exception('Private Canary resume and credential',response=response,body={'code':provider_code,'message':'Private Canary'})
    code,payload=failure_details(exc,'provider_request')
    assert code==expected
    assert payload['http_status']==status and payload['provider_code']==provider_code
    assert 'Private Canary' not in json.dumps(EventPayload.model_validate(payload).model_dump())


def test_untrusted_provider_code_is_not_echoed():
    response=httpx.Response(400,request=httpx.Request('POST','https://api.openai.com/v1/responses'))
    exc=BadRequestError('Private Canary',response=response,body={'code':'Private Canary'})
    _,payload=failure_details(exc,'provider_request')
    assert payload['provider_code']=='other'


def test_local_failure_identifies_stage_without_exception_text():
    code,payload=failure_details(AttributeError('Private Canary'),'preparing')
    assert code=='provider_or_validation_error' and payload=={'stage':'preparing','error_type':'AttributeError'}
