"""Add source, hash, page, and chunk metadata for bulk ingestion."""

from alembic import op
import sqlalchemy as sa


revision = "d7f1a9b2c3e4"
down_revision = "c5e9d2f8a1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("source_type", sa.String(length=20), server_default="student", nullable=False))
    op.add_column("chunks", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("chunk_index", sa.Integer(), server_default="0", nullable=False))
    op.add_column("chunks", sa.Column("source_type", sa.String(length=20), server_default="student", nullable=False))
    op.create_index("ix_documents_content_hash", "documents", ["subject_id", "name", "content_hash", "source_type"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_column("chunks", "source_type")
    op.drop_column("chunks", "chunk_index")
    op.drop_column("chunks", "page_number")
    op.drop_column("documents", "source_type")
    op.drop_column("documents", "content_hash")