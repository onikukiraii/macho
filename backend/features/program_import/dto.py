from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from features.exercise.types import BodyPart
from features.program.dto import PROGRAM_TEXT_MAX_LENGTH
from features.program.types import Weekday

PROGRAM_JSON_MAX_LENGTH = 200_000

_NO_CONTROL_OR_ZERO_WIDTH = r"^[^\x00-\x1f\x7f\u200b-\u200d\u2060\ufeff]+$"

ExerciseName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=_NO_CONTROL_OR_ZERO_WIDTH)
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DraftPlannedExerciseParams(_StrictModel):
    exercise: ExerciseName
    sets: int = Field(ge=1, le=20)
    reps: int = Field(ge=1, le=100)
    reps_max: int | None = Field(default=None, ge=1, le=100)
    target_rpe: float | None = Field(default=None, ge=1, le=10, allow_inf_nan=False)
    target_percent: float | None = Field(default=None, gt=0, le=120, allow_inf_nan=False)


class DraftDayParams(_StrictModel):
    day: int = Field(ge=1, le=7)
    weekday: Weekday
    exercises: list[DraftPlannedExerciseParams] = Field(min_length=1, max_length=20)


class DraftWeekParams(_StrictModel):
    week: int = Field(ge=1, le=52)
    label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]
    days: list[DraftDayParams] = Field(min_length=1, max_length=7)


class DraftExerciseParams(_StrictModel):
    name: ExerciseName
    body_part: BodyPart
    parent: ExerciseName | None = None
    coefficient: float | None = Field(default=None, gt=0, le=2, allow_inf_nan=False)
    e1rm_divisor: float | None = Field(default=None, gt=0, le=100, allow_inf_nan=False)
    increment_kg: float = Field(gt=0, le=20, allow_inf_nan=False)
    default_rest_seconds: int = Field(ge=1, le=900)


class ProgramDraftParams(_StrictModel):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=_NO_CONTROL_OR_ZERO_WIDTH)
    ]
    start_date: date
    tm_auto_update: bool
    design_note: str = Field(default="", max_length=PROGRAM_TEXT_MAX_LENGTH)
    new_exercises: list[DraftExerciseParams] = Field(default_factory=list, max_length=50)
    weeks: list[DraftWeekParams] = Field(min_length=1, max_length=52)


class ProgramImportParams(BaseModel):
    json_text: str = Field(max_length=PROGRAM_JSON_MAX_LENGTH)


class DraftIssueResponse(BaseModel):
    location: str
    message: str


class PreviewPlannedExerciseResponse(BaseModel):
    exercise_name: str
    is_new_exercise: bool
    sets: int
    reps: int
    reps_max: int | None
    target_rpe: float | None
    target_percent: float | None
    target_weight: float | None


class PreviewDayResponse(BaseModel):
    day: int
    weekday: Weekday
    exercises: list[PreviewPlannedExerciseResponse]


class PreviewWeekResponse(BaseModel):
    week: int
    label: str
    days: list[PreviewDayResponse]


class NewExerciseResponse(BaseModel):
    name: str
    body_part: BodyPart
    parent_name: str | None
    coefficient: float | None
    increment_kg: float
    default_rest_seconds: int


class ProgramPreviewValidResponse(BaseModel):
    status: Literal["valid"] = "valid"
    name: str
    start_date: date
    tm_auto_update: bool
    design_note: str
    new_exercises: list[NewExerciseResponse]
    weeks: list[PreviewWeekResponse]


class ProgramPreviewInvalidResponse(BaseModel):
    status: Literal["invalid"] = "invalid"
    issues: list[DraftIssueResponse]


ProgramPreviewResponse = Annotated[
    ProgramPreviewValidResponse | ProgramPreviewInvalidResponse, Field(discriminator="status")
]


class ProgramImportedResponse(BaseModel):
    uid: str
    name: str
