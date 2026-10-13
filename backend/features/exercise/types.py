from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExerciseKind(StrEnum):
    training_max = "training_max"
    derived = "derived"
    double_progression = "double_progression"


class TrainingMaxSource(StrEnum):
    auto = "auto"
    manual = "manual"


@dataclass(frozen=True)
class Exercise:
    id: int
    uid: str
    name: str
    parent_id: int | None
    coefficient: float | None
    e1rm_divisor: float | None
    increment_kg: float
    default_rest_seconds: int


@dataclass(frozen=True)
class TrainingMax:
    exercise_id: int
    value: float
    effective_at: datetime
    source: TrainingMaxSource
    reason: str


@dataclass(frozen=True)
class CalculationBasis:
    exercise_id: int
    name: str
    tm_owner_id: int | None
    coefficient: float
    e1rm_divisor: float
    increment_kg: float
    training_max: float | None


@dataclass(frozen=True)
class TrainingMaxUpdate:
    exercise_id: int
    exercise_name: str
    before: float
    after: float
    reason: str
