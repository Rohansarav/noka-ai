"""Persistent future workspace and research evidence."""
from alembic import op
import sqlalchemy as sa
revision = "0005"
down_revision = "0004"
branch_labels = depends_on = None


def upgrade():
    op.create_table("future_workspaces",
        sa.Column("profile_id", sa.String(64), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("scenario", sa.String(32), nullable=False),
        sa.Column("role_id", sa.String(80), sa.ForeignKey("roles.id")),
        sa.Column("weekly_hours", sa.Integer(), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("conversation", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("intelligence_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("intelligence_records")
    op.drop_table("future_workspaces")
