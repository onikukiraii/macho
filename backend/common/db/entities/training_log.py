from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.entities.base import Base


class TrainingLogRow(Base):
    __tablename__ = "training_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    program_day_id: Mapped[int | None] = mapped_column(ForeignKey("program_days.id"), nullable=True)
    memo: Mapped[str] = mapped_column(String(1000), nullable=False)

    performed_exercises: Mapped[list[PerformedExerciseRow]] = relationship(
        back_populates="training_log",
        cascade="all, delete-orphan",
        order_by="PerformedExerciseRow.sort_order, PerformedExerciseRow.id",
    )


class PerformedExerciseRow(Base):
    __tablename__ = "performed_exercises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    training_log_id: Mapped[int] = mapped_column(ForeignKey("training_logs.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    planned_exercise_id: Mapped[int | None] = mapped_column(ForeignKey("planned_exercises.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    memo: Mapped[str] = mapped_column(String(1000), nullable=False)

    training_log: Mapped[TrainingLogRow] = relationship(back_populates="performed_exercises")
    sets: Mapped[list[ExerciseSetRow]] = relationship(
        back_populates="performed_exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseSetRow.sort_order",
    )


class ExerciseSetRow(Base):
    __tablename__ = "exercise_sets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    performed_exercise_id: Mapped[int] = mapped_column(ForeignKey("performed_exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    rir: Mapped[int | None] = mapped_column(Integer, nullable=True)

    performed_exercise: Mapped[PerformedExerciseRow] = relationship(back_populates="sets")
