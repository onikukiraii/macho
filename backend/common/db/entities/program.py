from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.entities.base import Base
from common.db.utc_datetime import UtcDateTime


class ProgramRow(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    tm_auto_update: Mapped[bool] = mapped_column(Boolean, nullable=False)
    design_note: Mapped[str] = mapped_column(Text, nullable=False)

    weeks: Mapped[list[ProgramWeekRow]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramWeekRow.week",
    )


class ProgramWeekRow(Base):
    __tablename__ = "program_weeks"
    __table_args__ = (UniqueConstraint("program_id", "week"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)

    program: Mapped[ProgramRow] = relationship(back_populates="weeks")
    days: Mapped[list[ProgramDayRow]] = relationship(
        back_populates="program_week",
        cascade="all, delete-orphan",
        order_by="ProgramDayRow.day",
    )


class ProgramDayRow(Base):
    __tablename__ = "program_days"
    __table_args__ = (UniqueConstraint("program_week_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    program_week_id: Mapped[int] = mapped_column(ForeignKey("program_weeks.id"), nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday: Mapped[str] = mapped_column(String(3), nullable=False)

    program_week: Mapped[ProgramWeekRow] = relationship(back_populates="days")
    planned_exercises: Mapped[list[PlannedExerciseRow]] = relationship(
        back_populates="program_day",
        cascade="all, delete-orphan",
        order_by="PlannedExerciseRow.sort_order",
    )


class PlannedExerciseRow(Base):
    __tablename__ = "planned_exercises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    program_day_id: Mapped[int] = mapped_column(ForeignKey("program_days.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    program_day: Mapped[ProgramDayRow] = relationship(back_populates="planned_exercises")


class ProgramRulesRow(Base):
    __tablename__ = "program_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
