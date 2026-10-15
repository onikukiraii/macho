"""create program_rules

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATETIME_6 = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def upgrade() -> None:
    op.create_table(
        "program_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("updated_at", DATETIME_6, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("program_rules")
