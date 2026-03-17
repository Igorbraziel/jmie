"""add_language_column

Revision ID: fb15b3bb918e
Revises: 59338b97f1db
Create Date: 2026-03-10 15:33:38.840737

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb15b3bb918e'
down_revision: Union[str, Sequence[str], None] = '59338b97f1db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        'jobs',
        sa.Column('language', sa.String(length=2), nullable=True) 
    )


def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_column('jobs', 'language')
