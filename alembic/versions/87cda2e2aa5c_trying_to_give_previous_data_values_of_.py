"""trying to give previous data values of company

Revision ID: 87cda2e2aa5c
Revises: b9c9b8c6f3ad
Create Date: 2026-08-05 14:16:22.999734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87cda2e2aa5c'
down_revision: Union[str, Sequence[str], None] = 'b9c9b8c6f3ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("INSERT INTO companies (name, created_at) VALUES ('Default Org', now()) RETURNING id"))
    default_company_id = result.fetchone()[0] # type: ignore
    conn.execute(sa.text("UPDATE users SET company_id = :cid WHERE company_id IS NULL"), {"cid": default_company_id})
    conn.execute(sa.text("UPDATE leads SET company_id = :cid WHERE company_id IS NULL"), {"cid": default_company_id})



def downgrade() -> None:
    """Downgrade schema."""
    pass
