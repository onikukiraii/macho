from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.entities.base import Base


class ExerciseRow(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"), nullable=True)
    coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    e1rm_divisor: Mapped[float | None] = mapped_column(Float, nullable=True)
    increment_kg: Mapped[float] = mapped_column(Float, nullable=False)
    default_rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    training_maxes: Mapped[list[TrainingMaxRow]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="TrainingMaxRow.effective_at, TrainingMaxRow.id",
    )


class TrainingMaxRow(Base):
    __tablename__ = "training_maxes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    exercise: Mapped[ExerciseRow] = relationship(back_populates="training_maxes")


class TrainingMaxEvaluationRow(Base):
    __tablename__ = "training_max_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
