import datetime as dt

from pydantic import BaseModel

from features.exercise.types import BodyPart


class PeriodSummaryResponse(BaseModel):
    total_volume: float
    change_rate: float | None
    training_days: int
    set_count: int
    volume_per_training_day: float


class BodyPartVolumeResponse(BaseModel):
    body_part: BodyPart
    volume: float


class VolumeBucketResponse(BaseModel):
    start: dt.date
    volumes: list[BodyPartVolumeResponse]


class BodyPartShareResponse(BaseModel):
    body_part: BodyPart
    volume: float
    share: float


class MonthlyCumulativeVolumeResponse(BaseModel):
    month: int
    cumulative_volume: float


class AnnualVolumeResponse(BaseModel):
    year: int
    this_year: list[MonthlyCumulativeVolumeResponse]
    last_year: list[MonthlyCumulativeVolumeResponse]
    change_rate: float | None
    last_year_total_volume: float


class Big3LiftResponse(BaseModel):
    exercise_name: str
    e1rm: float | None


class Big3TotalResponse(BaseModel):
    lifts: list[Big3LiftResponse]
    total: float
    goal: float


class OverviewResponse(BaseModel):
    summary: PeriodSummaryResponse
    weekly_volumes: list[VolumeBucketResponse]
    monthly_volumes: list[VolumeBucketResponse]
    body_part_shares: list[BodyPartShareResponse]
    annual: AnnualVolumeResponse
    big3: Big3TotalResponse


class E1rmPointResponse(BaseModel):
    date: dt.date
    e1rm: float


class TrainingMaxPointResponse(BaseModel):
    effective_on: dt.date
    value: float


class ExerciseVolumeBucketResponse(BaseModel):
    start: dt.date
    volume: float


class ExerciseAnalyticsResponse(BaseModel):
    exercise_name: str
    max_weight: float | None
    max_e1rm: float | None
    total_volume: float
    e1rm_points: list[E1rmPointResponse]
    training_max_points: list[TrainingMaxPointResponse]
    weekly_volumes: list[ExerciseVolumeBucketResponse]
    monthly_volumes: list[ExerciseVolumeBucketResponse]
