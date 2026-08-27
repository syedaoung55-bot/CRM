"""adjusting some mistakes

Revision ID: 660aaf3e2271
Revises: 2296656d345e
Create Date: 2026-08-21 09:00:41.861975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '660aaf3e2271'
down_revision: Union[str, Sequence[str], None] = '2296656d345e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('tasks', 'is_compeleted', new_column_name='is_completed')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('tasks', 'is_completed', new_column_name='is_compeleted')