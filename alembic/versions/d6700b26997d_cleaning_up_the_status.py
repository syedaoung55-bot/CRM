"""cleaning up the status

Revision ID: d6700b26997d
Revises: 05afd81b9a5c
Create Date: 2026-08-15 16:22:55.018206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6700b26997d'
down_revision: Union[str, Sequence[str], None] = '05afd81b9a5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('leads', 'status')
    op.execute("DROP TYPE leadstatus")
    op.alter_column('leads', 'stage_id', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("CREATE TYPE leadstatus AS ENUM ('new','contacted','qualified','won','lost')")
    op.add_column('leads', sa.Column('status', sa.Enum('new','contacted','qualified','won','lost', name='leadstatus'), nullable=True))
    op.alter_column('leads', 'stage_id', nullable=True)
