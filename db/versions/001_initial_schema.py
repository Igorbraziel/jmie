"""initial_schema

Revision ID: 738c32c4dddc
Revises: 
Create Date: 2026-03-10 15:29:49.780983

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '738c32c4dddc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    - This file contains the instructions to apply the changes, on this case, create tables
    """

    # Sources TABLE
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('url', sa.String(), nullable=False, unique=False),
        sa.Column('country', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Companies TABLE
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Jobs TABLE (id is a SHA256 string to prevent duplicates)
    op.create_table(
        'jobs',
        sa.Column('id', sa.UUID(as_uuid=True), default=uuid.uuid4, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('url', sa.String(), unique=True, nullable=False),
        sa.Column('salary_min', sa.Numeric(), nullable=True),
        sa.Column('salary_max', sa.Numeric(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('job_type', sa.String(length=255), nullable=True),
        sa.Column('posted_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scraped_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('raw_data', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    

    # Creating Indexes for reading performance
    op.create_index('ix_jobs_source_id', 'jobs', ['source_id'])
    op.create_index('ix_jobs_company_id', 'jobs', ['company_id'])
    op.create_index('ix_jobs_url', 'jobs', ['url'])
    op.create_index('ix_jobs_posted_date', 'jobs', ['posted_date'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])


def downgrade() -> None:
    """Downgrade schema.
    - This file contains the exact inverse instructions to undo the changes, on this case, drop tables 
    """

    # Downgrades MUST execute in the exact reverse order of upgrades
    op.drop_index('ix_jobs_source_id', table_name='jobs')
    op.drop_index('ix_jobs_company_id', table_name='jobs')
    op.drop_index('ix_jobs_url', table_name='jobs')
    op.drop_index('ix_jobs_posted_date', table_name='jobs')
    op.drop_index('ix_jobs_created_at', table_name='jobs')

    op.drop_table('jobs')
    op.drop_table('companies')
    op.drop_table('sources')
