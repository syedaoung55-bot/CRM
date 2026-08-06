"""lock the column

Revision ID: 3c9545e10eff
Revises: 87cda2e2aa5c
Create Date: 2026-08-05 14:31:33.545005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c9545e10eff'
down_revision: Union[str, Sequence[str], None] = '87cda2e2aa5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'company_id', nullable=False)
    op.alter_column('leads', 'company_id', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    pass
