"""Source-backed software associations, separate from rated occupational requirements."""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = depends_on = None


def upgrade():
    op.create_table('role_technologies',
        sa.Column('role_id',sa.String(80),sa.ForeignKey('roles.id'),primary_key=True),
        sa.Column('skill_id',sa.String(40),sa.ForeignKey('skills.id'),primary_key=True),
        sa.Column('source_id',sa.String(64),sa.ForeignKey('sources.id'),nullable=False),
        sa.Column('classifications',sa.JSON(),nullable=False),
        sa.Column('hot_technology',sa.Boolean(),nullable=False),
        sa.Column('in_demand',sa.Boolean(),nullable=False))


def downgrade():
    op.drop_table('role_technologies')
