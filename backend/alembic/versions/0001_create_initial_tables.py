"""create initial tables

Revision ID: 0001
Revises:
Create Date: 2026-10-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATETIME_6 = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column(
            "name",
            sa.String(length=64).with_variant(mysql.VARCHAR(64, collation="utf8mb4_0900_as_cs"), "mysql"),
            nullable=False,
        ),
        sa.Column("body_part", sa.String(length=16), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("coefficient", sa.Float(), nullable=True),
        sa.Column("e1rm_divisor", sa.Float(), nullable=True),
        sa.Column("increment_kg", sa.Float(), nullable=False),
        sa.Column("default_rest_seconds", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["exercises.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("uid"),
    )
    op.create_table(
        "programs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("tm_auto_update", sa.Boolean(), nullable=False),
        sa.Column("design_note", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid"),
    )
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "endpoint",
            sa.String(length=500).with_variant(mysql.VARCHAR(500, collation="utf8mb4_0900_as_cs"), "mysql"),
            nullable=False,
        ),
        sa.Column("p256dh", sa.String(length=128), nullable=False),
        sa.Column("auth", sa.String(length=64), nullable=False),
        sa.Column("created_at", DATETIME_6, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_table(
        "rest_timers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("started_at", DATETIME_6, nullable=False),
        sa.Column("ends_at", DATETIME_6, nullable=False),
        sa.Column("total_seconds", sa.Integer(), nullable=False),
        sa.Column("next_set_label", sa.String(length=100), nullable=False),
        sa.CheckConstraint("slot = 1", name="ck_rest_timers_slot"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot"),
        sa.UniqueConstraint("uid"),
    )
    op.create_table(
        "training_max_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("created_at", DATETIME_6, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start"),
    )
    op.create_table(
        "program_weeks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "week"),
    )
    op.create_table(
        "training_maxes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("effective_at", DATETIME_6, nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "program_days",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("program_week_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.String(length=3), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_week_id"],
            ["program_weeks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_week_id", "day"),
        sa.UniqueConstraint("uid"),
    )
    op.create_table(
        "planned_exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_day_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("reps_max", sa.Integer(), nullable=True),
        sa.Column("target_rpe", sa.Float(), nullable=True),
        sa.Column("target_percent", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
        ),
        sa.ForeignKeyConstraint(
            ["program_day_id"],
            ["program_days.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "training_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("program_day_id", sa.Integer(), nullable=True),
        sa.Column("memo", sa.String(length=1000), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_day_id"],
            ["program_days.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid"),
    )
    op.create_index(op.f("ix_training_logs_date"), "training_logs", ["date"], unique=False)
    op.create_table(
        "performed_exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=36), nullable=False),
        sa.Column("training_log_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("planned_exercise_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("memo", sa.String(length=1000), nullable=False),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
        ),
        sa.ForeignKeyConstraint(
            ["planned_exercise_id"],
            ["planned_exercises.id"],
        ),
        sa.ForeignKeyConstraint(
            ["training_log_id"],
            ["training_logs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid"),
    )
    op.create_table(
        "exercise_sets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("performed_exercise_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("rir", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["performed_exercise_id"],
            ["performed_exercises.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("performed_exercise_id", "sort_order"),
    )


def downgrade() -> None:
    raise NotImplementedError
