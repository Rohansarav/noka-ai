from alembic import context
from backend.app.database import engine
from backend.app.models import Base

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
