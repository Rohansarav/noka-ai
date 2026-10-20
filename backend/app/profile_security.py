"""Anonymous ownership and same-origin mutation guard; raw tokens are never persisted."""
import hashlib
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from backend.app.config import get_settings
from backend.app.models import PrivateSession, Profile

COOKIE = "noka_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def active_session(request, db):
    token = request.cookies.get(COOKIE, "")
    if not 20 <= len(token) <= 128:
        return None
    record = db.get(PrivateSession, token_hash(token))
    return record if record and record.expires_at > datetime.now(timezone.utc) else None


def owned_profile(profile_id, request, db):
    owner = active_session(request, db)
    profile = db.get(Profile, profile_id) if owner else None
    if not profile or profile.session_hash != owner.token_hash:
        raise HTTPException(404)
    return profile


def same_origin(request: Request):
    """A custom header blocks simple-form CSRF; exact origins and strict cookies add defence."""
    expected = (get_settings().public_origin or str(request.base_url)).rstrip("/")
    if request.headers.get("x-noka-csrf") != "1" or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403)
    origin = request.headers.get("origin")
    if origin and origin != expected:
        raise HTTPException(403)


class ProfileBodyLimit:
    """Bound resume and agent bodies before parsing or spooling arbitrary input."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(("/api/profiles", "/api/agent-executions")) or scope["method"] not in {"POST", "PUT"}:
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse
        limit = 8192 if scope["path"].startswith("/api/agent-executions") else 5 * 1024 * 1024 + 65536
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                agent = scope["path"].startswith("/api/agent-executions")
                return await JSONResponse({"error": {"code": "request_too_large" if agent else "upload_too_large", "message": "Agent request exceeds 8 KB." if agent else "Maximum upload size is 5 MB."}}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        async def bounded_receive():
            return chunks.pop(0) if chunks else {"type": "http.disconnect"}
        await self.app(scope, bounded_receive, send)
