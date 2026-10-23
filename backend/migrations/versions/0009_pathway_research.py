"""Private job-grounded pathway revisions."""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = depends_on = None


def upgrade():
    op.create_table('pathway_research',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('profile_id', sa.String(64), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.String(80), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False))
    op.create_index('ix_pathway_research_profile_id', 'pathway_research', ['profile_id'])


def downgrade():
    op.drop_table('pathway_research')
