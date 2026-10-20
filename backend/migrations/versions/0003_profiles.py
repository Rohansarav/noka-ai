"""Private anonymous profiles; public evidence tables are unchanged."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("private_sessions", sa.Column("token_hash", sa.String(64), primary_key=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("profiles", sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("session_hash", sa.String(64), sa.ForeignKey("private_sessions.token_hash"), unique=True, nullable=False),
        sa.Column("country", sa.String(2), nullable=False), sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False), sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("profile_skills", sa.Column("profile_id", sa.String(64), sa.ForeignKey("profiles.id"), primary_key=True),
        sa.Column("skill_id", sa.String(40), sa.ForeignKey("skills.id"), primary_key=True),
        sa.Column("level", sa.String(16), nullable=False), sa.Column("years", sa.Float(), nullable=True))


def downgrade():
    op.drop_table("profile_skills")
    op.drop_table("profiles")
    op.drop_table("private_sessions")
