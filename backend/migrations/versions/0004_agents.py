"""Persistent bounded execution journal; private session deletion cascades."""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("agent_executions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("session_hash", sa.String(64), sa.ForeignKey("private_sessions.token_hash", ondelete="CASCADE"), nullable=False),
        sa.Column("agent", sa.String(24), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("model", sa.String(100), nullable=False),
        sa.Column("tool_count", sa.Integer(), nullable=False), sa.Column("token_usage", sa.Integer(), nullable=False),
        sa.Column("event_sequence", sa.Integer(), nullable=False), sa.Column("error_code", sa.String(40)), sa.Column("result", sa.JSON()))
    op.create_index("ix_agent_executions_session_hash", "agent_executions", ["session_hash"])
    op.create_table("agent_events",
        sa.Column("execution_id", sa.String(64), sa.ForeignKey("agent_executions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sequence", sa.Integer(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent", sa.String(24), nullable=False), sa.Column("type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("message", sa.String(200), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("agent_events")
    op.drop_index("ix_agent_executions_session_hash", table_name="agent_executions")
    op.drop_table("agent_executions")
