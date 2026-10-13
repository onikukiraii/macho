from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from features.exercise.types import Exercise, TrainingMaxUpdate
from features.program.types import PlannedExercise, Program, ProgramDay, ProgramWeek


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


@dataclass(frozen=True)
class NewPerformedExercise:
    uid: str
    exercise_id: int
    planned_exercise_id: int | None
    order: int


@dataclass(frozen=True)
class PreviousPerformance:
    date: date
    sets: tuple[ExerciseSet, ...]


@dataclass(frozen=True)
class ExerciseHistoryEntry:
    training_log_uid: str
    date: date
    program_day_id: int | None
    sets: tuple[ExerciseSet, ...]


@dataclass(frozen=True)
class ScheduledDay:
    week: ProgramWeek
    day: ProgramDay
    guide_date: date


@dataclass(frozen=True)
class DayOption:
    scheduled_day: ScheduledDay
    is_next: bool
    last_recorded_on: date | None


@dataclass(frozen=True)
class ProgramProgress:
    program: Program
    day_statuses: dict[int, DayStatus]


@dataclass(frozen=True)
class TopSet:
    exercise_name: str
    exercise_set: ExerciseSet


@dataclass(frozen=True)
class TrainingLogSummary:
    training_log: TrainingLog
    scheduled_day: ScheduledDay | None
    top_sets: tuple[TopSet, ...]


@dataclass(frozen=True)
class PreviousResult:
    date: date
    top_set: ExerciseSet
    sets: tuple[ExerciseSet, ...]


@dataclass(frozen=True)
class PerformedExerciseDetail:
    performed: PerformedExercise
    exercise: Exercise
    planned: PlannedExercise | None
    target_weight: float | None
    previous: PreviousResult | None


@dataclass(frozen=True)
class TrainingLogDetail:
    training_log: TrainingLog
    scheduled_day: ScheduledDay | None
    exercises: tuple[PerformedExerciseDetail, ...]


@dataclass(frozen=True)
class TrainingLogCreated:
    training_log: TrainingLog
    training_max_updates: tuple[TrainingMaxUpdate, ...]


@dataclass(frozen=True)
class ExerciseHistoryRecord:
    entry: ExerciseHistoryEntry
    scheduled_day: ScheduledDay | None
