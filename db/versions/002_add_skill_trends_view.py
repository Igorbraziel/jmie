"""add_skill_trends_view

Revision ID: 59338b97f1db
Revises: 738c32c4dddc
Create Date: 2026-03-10 15:33:23.321769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59338b97f1db'
down_revision: Union[str, Sequence[str], None] = '738c32c4dddc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE VIEW skill_trends AS
        SELECT
            DATE(scraped_at) AS scraped_date,
            source_id,
            COUNT(id) AS total_jobs
        FROM jobs
        GROUP BY DATE(scraped_at), source_id; 
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        DROP VIEW IF EXISTS skill_trends;
    """)
