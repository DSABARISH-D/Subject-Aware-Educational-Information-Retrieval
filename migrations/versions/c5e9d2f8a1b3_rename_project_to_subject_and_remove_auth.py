"""Rename project concept to subject and remove auth user tables

Revision ID: c5e9d2f8a1b3
Revises: 003a10cca4c5
Create Date: 2026-09-15 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c5e9d2f8a1b3'
down_revision: Union[str, Sequence[str], None] = '003a10cca4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Rename projects table to subjects
    op.rename_table('projects', 'subjects')
    
    # 2. Drop owner_id column from subjects
    try:
        op.drop_constraint('projects_owner_id_fkey', 'subjects', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_column('subjects', 'owner_id')
    except Exception:
        pass

    # 3. Drop users table
    try:
        op.drop_table('users')
    except Exception:
        pass

    # 4. Update documents table (project_id -> subject_id)
    try:
        op.drop_constraint('documents_project_id_fkey', 'documents', type_='foreignkey')
    except Exception:
        pass
    op.alter_column('documents', 'project_id', new_column_name='subject_id')
    op.create_foreign_key('documents_subject_id_fkey', 'documents', 'subjects', ['subject_id'], ['id'])

    # 5. Update ingestion_jobs table (project_id -> subject_id, drop user_id)
    try:
        op.drop_constraint('ingestion_jobs_project_id_fkey', 'ingestion_jobs', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('ingestion_jobs_user_id_fkey', 'ingestion_jobs', type_='foreignkey')
    except Exception:
        pass
    op.alter_column('ingestion_jobs', 'project_id', new_column_name='subject_id')
    op.create_foreign_key('ingestion_jobs_subject_id_fkey', 'ingestion_jobs', 'subjects', ['subject_id'], ['id'])
    try:
        op.drop_column('ingestion_jobs', 'user_id')
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('ingestion_jobs', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.alter_column('ingestion_jobs', 'subject_id', new_column_name='project_id')
    op.alter_column('documents', 'subject_id', new_column_name='project_id')
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('auth0_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('picture', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.add_column('subjects', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.rename_table('subjects', 'projects')
