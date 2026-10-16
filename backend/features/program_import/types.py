from dataclasses import dataclass
from datetime import date

from features.exercise.types import BodyPart
from features.program.types import Weekday


@dataclass(frozen=True)
class DraftPlannedExercise:
    exercise_name: str
    sets: int
    reps: int
    reps_max: int | None
    target_rpe: float | None
    target_percent: float | None


@dataclass(frozen=True)
class DraftDay:
    day: int
    weekday: Weekday
    exercises: tuple[DraftPlannedExercise, ...]


@dataclass(frozen=True)
class DraftWeek:
    week: int
    label: str
    days: tuple[DraftDay, ...]


@dataclass(frozen=True)
class DraftExercise:
    name: str
    body_part: BodyPart
    parent_name: str | None
    coefficient: float | None
    e1rm_divisor: float | None
    increment_kg: float
    default_rest_seconds: int


@dataclass(frozen=True)
class ProgramDraft:
    name: str
    start_date: date
    tm_auto_update: bool
    design_note: str
    new_exercises: tuple[DraftExercise, ...]
    weeks: tuple[DraftWeek, ...]


@dataclass(frozen=True)
class DraftIssue:
    location: str
    message: str


@dataclass(frozen=True)
class DraftRejected:
    issues: tuple[DraftIssue, ...]


@dataclass(frozen=True)
class PreviewPlannedExercise:
    planned: DraftPlannedExercise
    is_new_exercise: bool
    target_weight: float | None


@dataclass(frozen=True)
class PreviewDay:
    day: int
    weekday: Weekday
    exercises: tuple[PreviewPlannedExercise, ...]


@dataclass(frozen=True)
class PreviewWeek:
    week: int
    label: str
    days: tuple[PreviewDay, ...]


@dataclass(frozen=True)
class ProgramPreview:
    draft: ProgramDraft
    weeks: tuple[PreviewWeek, ...]
