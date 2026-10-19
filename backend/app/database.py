from sqlalchemy import create_engine
from backend.app.config import get_settings


def make_engine():
    """Normalize hosted PostgreSQL URLs and retain the local SQLite fallback."""
    url = get_settings().database_url
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    kwargs = {"check_same_thread": False} if url.startswith("sqlite") else {"connect_timeout": 5}
    return create_engine(url, connect_args=kwargs, pool_pre_ping=True, hide_parameters=True)


engine = make_engine()
