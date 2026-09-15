"""Ensure pgvector is available for the existing embedding column."""

from alembic import op


revision = "e8c2d4f6a1b3"
down_revision = "d7f1a9b2c3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Do not remove the extension because other databases or applications may use it.
    pass