from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from features.exercise.types import BodyPart


class BucketUnit(StrEnum):
    week = "week"
    month = "month"


@dataclass(frozen=True)
class PeriodSummary:
    total_volume: float
    change_rate: float | None
    training_days: int
    set_count: int
    volume_per_training_day: float


@dataclass(frozen=True)
class BodyPartVolume:
    body_part: BodyPart
    volume: float


@dataclass(frozen=True)
class VolumeBucket:
    start: date
    volumes: tuple[BodyPartVolume, ...]


@dataclass(frozen=True)
class BodyPartShare:
    body_part: BodyPart
    volume: float
    share: float


@dataclass(frozen=True)
class MonthlyCumulativeVolume:
    month: int
    cumulative_volume: float


@dataclass(frozen=True)
class AnnualVolume:
    year: int
    this_year: tuple[MonthlyCumulativeVolume, ...]
    last_year: tuple[MonthlyCumulativeVolume, ...]
    change_rate: float | None
    last_year_total_volume: float


@dataclass(frozen=True)
class Big3Lift:
    exercise_name: str
    e1rm: float | None


@dataclass(frozen=True)
class Big3Total:
    lifts: tuple[Big3Lift, ...]
    total: float
    goal: float


@dataclass(frozen=True)
class Overview:
    summary: PeriodSummary
    weekly_volumes: tuple[VolumeBucket, ...]
    monthly_volumes: tuple[VolumeBucket, ...]
    body_part_shares: tuple[BodyPartShare, ...]
    annual: AnnualVolume
    big3: Big3Total


@dataclass(frozen=True)
class E1rmPoint:
    date: date
    e1rm: float


@dataclass(frozen=True)
class TrainingMaxPoint:
    effective_on: date
    value: float


@dataclass(frozen=True)
class ExerciseVolumeBucket:
    start: date
    volume: float


@dataclass(frozen=True)
class ExerciseAnalytics:
    exercise_name: str
    max_weight: float | None
    max_e1rm: float | None
    total_volume: float
    e1rm_points: tuple[E1rmPoint, ...]
    training_max_points: tuple[TrainingMaxPoint, ...]
    weekly_volumes: tuple[ExerciseVolumeBucket, ...]
    monthly_volumes: tuple[ExerciseVolumeBucket, ...]
