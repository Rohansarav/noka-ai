"""Private resumable onboarding; existing confirmed profiles remain complete."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = depends_on = None


def upgrade():
    op.add_column("profiles", sa.Column("onboarding", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("profiles", "onboarding")
