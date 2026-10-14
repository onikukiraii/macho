import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator

from features.program.types import Weekday
from features.training_log.types import DayStatus


class SetParams(BaseModel):
    order: int = Field(ge=1, le=50)
    weight: float = Field(ge=0, le=500, allow_inf_nan=False)
    reps: int = Field(ge=0, le=100)
    rir: int | None = Field(ge=0, le=10)


class SetResponse(BaseModel):
    order: int
    weight: float
    reps: int
    rir: int | None


class TopSetResponse(BaseModel):
    exercise_name: str
    weight: float
    reps: int
    rir: int | None


class TrainingLogSummaryResponse(BaseModel):
    uid: str
    date: dt.date
    day_label: str | None
    week_label: str | None
    top_sets: list[TopSetResponse]


class DayOptionResponse(BaseModel):
    program_day_uid: str
    week: int
    week_label: str
    day: int
    weekday: Weekday
    guide_date: dt.date
    is_next: bool
    last_recorded_on: dt.date | None


class DayOptionsResponse(BaseModel):
    options: list[DayOptionResponse]


class TrainingLogCreateParams(BaseModel):
    date: dt.date
    program_day_uid: str | None


class TrainingMaxUpdateResponse(BaseModel):
    exercise_name: str
    before: float
    after: float


class TrainingLogCreatedResponse(BaseModel):
    uid: str
    training_max_updates: list[TrainingMaxUpdateResponse]


class PlannedResponse(BaseModel):
    sets: int
    reps: int
    reps_max: int | None
    target_rpe: float | None
    target_percent: float | None


class PreviousResultResponse(BaseModel):
    date: dt.date
    top_set: SetResponse
    sets: list[SetResponse]


class PerformedExerciseResponse(BaseModel):
    uid: str
    exercise_uid: str
    exercise_name: str
    planned: PlannedResponse | None
    target_weight: float | None
    previous: PreviousResultResponse | None
    default_rest_seconds: int
    memo: str
    sets: list[SetResponse]


class TrainingLogDetailResponse(BaseModel):
    uid: str
    date: dt.date
    day_label: str | None
    week_label: str | None
    guide_date: dt.date | None
    memo: str
    exercises: list[PerformedExerciseResponse]


class TrainingLogUpdateParams(BaseModel):
    memo: str = Field(max_length=1000)


class PerformedExerciseCreateParams(BaseModel):
    exercise_uid: str


class PerformedExerciseReplaceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_uid: str = Field(min_length=1, max_length=36)


class PerformedExerciseMemoUpdateParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memo: str = Field(max_length=1000)


class SetsReplaceParams(BaseModel):
    sets: list[SetParams] = Field(max_length=50)

    @field_validator("sets")
    @classmethod
    def validate_unique_orders(cls, sets: list[SetParams]) -> list[SetParams]:
        orders = [exercise_set.order for exercise_set in sets]
        if len(set(orders)) != len(orders):
            raise ValueError("同じセット番号が複数あります")
        return sets


class ExerciseHistoryEntryResponse(BaseModel):
    training_log_uid: str
    date: dt.date
    day_label: str | None
    sets: list[SetResponse]


class ProgramDayProgressResponse(BaseModel):
    program_day_uid: str
    day: int
    weekday: Weekday
    status: DayStatus


class ProgramWeekProgressResponse(BaseModel):
    week: int
    label: str
    days: list[ProgramDayProgressResponse]


class ProgramProgressResponse(BaseModel):
    name: str
    start_date: dt.date
    week_count: int
    tm_auto_update: bool
    design_note: str
    weeks: list[ProgramWeekProgressResponse]


class SetCountResponse(BaseModel):
    count: int
