from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class Weekday(StrEnum):
    mon = "mon"
    tue = "tue"
    wed = "wed"
    thu = "thu"
    fri = "fri"
    sat = "sat"
    sun = "sun"


@dataclass(frozen=True)
class PlannedExercise:
    id: int
    exercise_id: int
    order: int
    sets: int
    reps: int
    reps_max: int | None
    target_rpe: float | None
    target_percent: float | None


@dataclass(frozen=True)
class ProgramDay:
    id: int
    uid: str
    day: int
    weekday: Weekday
    planned_exercises: tuple[PlannedExercise, ...]


@dataclass(frozen=True)
class ProgramWeek:
    week: int
    label: str
    days: tuple[ProgramDay, ...]


@dataclass(frozen=True)
class ProgramDayInWeek:
    week: ProgramWeek
    day: ProgramDay


@dataclass(frozen=True)
class Program:
    id: int
    uid: str
    name: str
    start_date: date
    tm_auto_update: bool
    design_note: str
    weeks: tuple[ProgramWeek, ...]


@dataclass(frozen=True)
class NewPlannedExercise:
    exercise_id: int
    order: int
    sets: int
    reps: int
    reps_max: int | None
    target_rpe: float | None
    target_percent: float | None


@dataclass(frozen=True)
class NewProgramDay:
    day: int
    weekday: Weekday
    planned_exercises: tuple[NewPlannedExercise, ...]


@dataclass(frozen=True)
class NewProgramWeek:
    week: int
    label: str
    days: tuple[NewProgramDay, ...]


@dataclass(frozen=True)
class NewProgram:
    name: str
    start_date: date
    tm_auto_update: bool
    design_note: str
    weeks: tuple[NewProgramWeek, ...]


@dataclass(frozen=True)
class PastProgram:
    program: Program
    end_date: date


@dataclass(frozen=True)
class ProgramRules:
    body: str
    updated_at: datetime | None
