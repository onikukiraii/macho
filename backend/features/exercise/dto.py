from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from features.exercise.types import ExerciseKind, TrainingMaxSource

_NO_CONTROL_OR_ZERO_WIDTH = r"^[^\x00-\x1f\x7f\u200b-\u200d\u2060\ufeff]+$"


class ExerciseResponse(BaseModel):
    uid: str
    name: str
    kind: ExerciseKind
    parent_uid: str | None
    parent_name: str | None
    coefficient: float | None
    e1rm_divisor: float
    increment_kg: float
    default_rest_seconds: int
    current_training_max: float | None


class TrainingMaxResponse(BaseModel):
    value: float
    effective_at: datetime
    source: TrainingMaxSource
    reason: str


class ExerciseDetailResponse(BaseModel):
    exercise: ExerciseResponse
    training_max_history: list[TrainingMaxResponse]


class ExerciseSaveParams(BaseModel):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=_NO_CONTROL_OR_ZERO_WIDTH)
    ]
    parent_uid: str | None
    coefficient: float | None = Field(gt=0, le=2, allow_inf_nan=False)
    e1rm_divisor: float | None = Field(gt=0, le=100, allow_inf_nan=False)
    increment_kg: float = Field(gt=0, le=20, allow_inf_nan=False)
    default_rest_seconds: int = Field(ge=1, le=900)


class TrainingMaxCreateParams(BaseModel):
    value: float = Field(gt=0, le=500, allow_inf_nan=False)
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255, pattern=_NO_CONTROL_OR_ZERO_WIDTH)
    ]
