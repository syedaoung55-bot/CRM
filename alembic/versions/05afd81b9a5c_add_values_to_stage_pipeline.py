"""add values to stage pipeline

Revision ID: 05afd81b9a5c
Revises: 3ab1feb4f524
Create Date: 2026-08-15 15:58:06.689145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05afd81b9a5c'
down_revision: Union[str, Sequence[str], None] = '3ab1feb4f524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    companies = conn.execute(sa.text("SELECT id FROM companies")).fetchall()

    stage_defs = [
        ("New", 1, False, False),
        ("Contacted", 2, False, False),
        ("Qualified", 3, False, False),
        ("Won", 4, True, False),
        ("Lost", 5, False, True),
    ]
    status_to_name = {"new": "New", "contacted": "Contacted", "qualified": "Qualified",
                       "won": "Won", "lost": "Lost"}

    for (company_id,) in companies:
        name_to_stage_id = {}
        for name, order, is_won, is_lost in stage_defs:
            result = conn.execute(sa.text(
                'INSERT INTO pipeline_stages (company_id, name, "order", is_won, is_lost, created_at) '
                'VALUES (:cid, :name, :order, :won, :lost, now()) RETURNING id'
            ), {"cid": company_id, "name": name, "order": order, "won": is_won, "lost": is_lost})
            name_to_stage_id[name] = result.fetchone()[0] # type: ignore

        for status_val, stage_name in status_to_name.items():
            conn.execute(sa.text(
                "UPDATE leads SET stage_id = :sid WHERE company_id = :cid AND status = :status"
            ), {"sid": name_to_stage_id[stage_name], "cid": company_id, "status": status_val})



def downgrade() -> None:
    """Downgrade schema."""
    pass
