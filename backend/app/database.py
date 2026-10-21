from sqlalchemy import create_engine, event
from backend.app.config import get_settings


def make_engine():
    """Normalize hosted PostgreSQL URLs and retain the local SQLite fallback."""
    url = get_settings().database_url
    if get_settings().environment == "production" and not url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Production requires persistent PostgreSQL; SQLite is development-only.")
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    kwargs = {"check_same_thread": False} if url.startswith("sqlite") else {"connect_timeout": 5}
    result = create_engine(url, connect_args=kwargs, pool_pre_ping=True, hide_parameters=True)
    if url.startswith("sqlite"):
        @event.listens_for(result, "connect")
        def enforce_foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
    return result


engine = make_engine()
