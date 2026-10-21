"""Keep confirmed analysis context separate from editable profile drafts."""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = depends_on = None


def upgrade():
    op.add_column('profiles', sa.Column('analysis_context', sa.JSON(), nullable=True))
    op.execute(sa.text('UPDATE profiles SET analysis_context = onboarding WHERE confirmed = true'))


def downgrade():
    op.drop_column('profiles', 'analysis_context')
