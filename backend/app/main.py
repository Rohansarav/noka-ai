import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from backend.app.agents.api import router as agent_router
from backend.app.config import get_settings
from backend.app.database import engine
from backend.app.evidence_api import router as evidence_router
from backend.app.profile_api import router as profile_router
from backend.app.profile_security import ProfileBodyLimit
from backend.app.career_graph_api import router as career_graph_router
from backend.app.future import router as future_router

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
app = FastAPI(title="Noka API", version="0.1.0")
logger = logging.getLogger("noka")
app.include_router(agent_router)
app.include_router(future_router)
app.include_router(evidence_router)
app.include_router(career_graph_router)
app.include_router(profile_router)
app.add_middleware(ProfileBodyLimit)
if get_settings().environment == "development":
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET"], allow_headers=["Content-Type"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["noka-api"] = "noka-api"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["connected"] = "connected"
    migration: Literal["current"] = "current"
    frontend: Literal["built", "dev"]


def error(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.error("Database unavailable (%s)", type(exc).__name__)
    return error(503, "database_unavailable", "Evidence database unavailable; last-successful imports have not been replaced.")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error(exc.status_code, "not_found" if exc.status_code == 404 else "request_error", "Resource not found." if exc.status_code == 404 else "Request could not be completed.")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error(422, "validation_error", "Request validation failed.")


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Never log exception text, request bodies or URLs, which may contain PII.
    logger.error("Unhandled API error (%s)", type(exc).__name__)
    return error(500, "internal_error", "An unexpected error occurred.")


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@app.get("/api/ready", response_model=ReadyResponse, responses={503: {"description": "Dependency unavailable"}})
def ready():
    """Probe database connectivity, migration revision and the production bundle."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != "0006":
                return error(503, "schema_unavailable", "Database migrations are required.")
    except Exception:
        return error(503, "database_unavailable", "Database or migrations unavailable.")
    if get_settings().environment != "development" and not (DIST / "index.html").is_file():
        return error(503, "frontend_unavailable", "Frontend build unavailable.")
    return ReadyResponse(frontend="built" if (DIST / "index.html").is_file() else "dev")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    """Serve real assets and client routes without masking missing API routes."""
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404)
    target = (DIST / path).resolve()
    if not target.is_relative_to(DIST.resolve()):
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    if path.startswith("assets/") or Path(path).suffix:
        raise HTTPException(404)
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    return error(503, "frontend_unavailable", "Build the frontend or run the Vite development server.")
