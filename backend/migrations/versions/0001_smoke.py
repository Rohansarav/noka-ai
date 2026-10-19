"""Phase 0 migration smoke table."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("schema_smoke", sa.Column("id", sa.Integer, primary_key=True))


def downgrade():
    op.drop_table("schema_smoke")
