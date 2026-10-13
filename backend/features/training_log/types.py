from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class DayStatus(StrEnum):
    done = "done"
    missed = "missed"
    next = "next"
    pending = "pending"


@dataclass(frozen=True)
class ExerciseSet:
    order: int
    weight: float
    reps: int
    rir: int | None


@dataclass(frozen=True)
class PerformedExercise:
    id: int
    uid: str
    exercise_id: int
    planned_exercise_id: int | None
    order: int
    memo: str
    sets: tuple[ExerciseSet, ...]


@dataclass(frozen=True)
class TrainingLog:
    id: int
    uid: str
    date: date
    program_day_id: int | None
    memo: str
    exercises: tuple[PerformedExercise, ...]
