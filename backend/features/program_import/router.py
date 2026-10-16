from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from common.errors import BusinessRuleViolation, Conflict, NotFound
from dependencies import get_exercise_repository, get_program_repository, get_today, get_training_log_repository
from features.exercise.protocol import ExerciseRepository
from features.program.protocol import ProgramRepository
from features.program_import import service
from features.program_import.dto import (
    DraftIssueResponse,
    NewExerciseResponse,
    PreviewDayResponse,
    PreviewPlannedExerciseResponse,
    PreviewWeekResponse,
    ProgramDraftParams,
    ProgramImportedResponse,
    ProgramImportParams,
    ProgramPreviewInvalidResponse,
    ProgramPreviewResponse,
    ProgramPreviewValidResponse,
)
from features.program_import.types import (
    DraftDay,
    DraftExercise,
    DraftPlannedExercise,
    DraftRejected,
    DraftWeek,
    ProgramDraft,
    ProgramPreview,
)
from features.training_log.protocol import TrainingLogRepository

router = APIRouter(prefix="/api/program-imports", tags=["program-imports"])

INVALID_JSON_LOCATION = "JSON 全体"
INVALID_JSON_MESSAGE = "JSON として読み込めません"
MISSING_FIELD_MESSAGE = "必須の項目がありません"

_ERROR_MESSAGES = {
    "json_invalid": INVALID_JSON_MESSAGE,
    "missing": MISSING_FIELD_MESSAGE,
    "extra_forbidden": "定義されていない項目です",
    "enum": "指定できない値です",
    "greater_than": "値が小さすぎます",
    "greater_than_equal": "値が小さすぎます",
    "less_than": "値が大きすぎます",
    "less_than_equal": "値が大きすぎます",
    "string_too_short": "文字数が足りません",
    "string_too_long": "文字数が多すぎます",
    "too_short": "件数が足りません",
    "too_long": "件数が多すぎます",
    "string_pattern_mismatch": "使用できない文字が含まれています",
}

ProgramRepositoryDep = Annotated[ProgramRepository, Depends(get_program_repository)]
ExerciseRepositoryDep = Annotated[ExerciseRepository, Depends(get_exercise_repository)]
TrainingLogRepositoryDep = Annotated[TrainingLogRepository, Depends(get_training_log_repository)]
TodayDep = Annotated[date, Depends(get_today)]


@router.post("/preview")
def create_program_preview(
    params: ProgramImportParams,
    program_repo: ProgramRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    training_log_repo: TrainingLogRepositoryDep,
    today: TodayDep,
) -> ProgramPreviewResponse:
    try:
        draft_params = ProgramDraftParams.model_validate_json(params.json_text)
    except ValidationError as e:
        return ProgramPreviewInvalidResponse(issues=_to_issue_responses(e))
    result = service.preview_program(
        program_repo=program_repo,
        exercise_repo=exercise_repo,
        training_log_repo=training_log_repo,
        draft=_to_draft(draft_params),
        today=today,
    )
    if isinstance(result, DraftRejected):
        return ProgramPreviewInvalidResponse(
            issues=[DraftIssueResponse(location=issue.location, message=issue.message) for issue in result.issues]
        )
    return _to_preview_response(result)


@router.post("")
def create_program_import(
    params: ProgramImportParams,
    program_repo: ProgramRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    training_log_repo: TrainingLogRepositoryDep,
    today: TodayDep,
) -> ProgramImportedResponse:
    try:
        draft_params = ProgramDraftParams.model_validate_json(params.json_text)
    except ValidationError as e:
        raise HTTPException(422, [issue.model_dump() for issue in _to_issue_responses(e)]) from e
    try:
        program = service.import_program(
            program_repo=program_repo,
            exercise_repo=exercise_repo,
            training_log_repo=training_log_repo,
            draft=_to_draft(draft_params),
            today=today,
        )
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    except Conflict as e:
        raise HTTPException(409, str(e)) from e
    return ProgramImportedResponse(uid=program.uid, name=program.name)


def _to_issue_responses(error: ValidationError) -> list[DraftIssueResponse]:
    return [
        DraftIssueResponse(location=_format_location(detail["loc"]), message=_describe_error(detail["type"]))
        for detail in error.errors()
    ]


def _format_location(loc: tuple[int | str, ...]) -> str:
    if len(loc) == 0:
        return INVALID_JSON_LOCATION
    location = ""
    for part in loc:
        location += f"[{part}]" if isinstance(part, int) else f".{part}"
    return location.removeprefix(".")


def _describe_error(error_type: str) -> str:
    if error_type in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[error_type]
    if error_type.endswith(("_type", "_parsing")):
        return "型が正しくありません"
    return "値が正しくありません"


def _to_draft(params: ProgramDraftParams) -> ProgramDraft:
    return ProgramDraft(
        name=params.name,
        start_date=params.start_date,
        tm_auto_update=params.tm_auto_update,
        design_note=params.design_note,
        new_exercises=tuple(
            DraftExercise(
                name=exercise.name,
                body_part=exercise.body_part,
                parent_name=exercise.parent,
                coefficient=exercise.coefficient,
                e1rm_divisor=exercise.e1rm_divisor,
                increment_kg=exercise.increment_kg,
                default_rest_seconds=exercise.default_rest_seconds,
            )
            for exercise in params.new_exercises
        ),
        weeks=tuple(
            DraftWeek(
                week=week.week,
                label=week.label,
                days=tuple(
                    DraftDay(
                        day=day.day,
                        weekday=day.weekday,
                        exercises=tuple(
                            DraftPlannedExercise(
                                exercise_name=planned.exercise,
                                sets=planned.sets,
                                reps=planned.reps,
                                reps_max=planned.reps_max,
                                target_rpe=planned.target_rpe,
                                target_percent=planned.target_percent,
                            )
                            for planned in day.exercises
                        ),
                    )
                    for day in week.days
                ),
            )
            for week in params.weeks
        ),
    )


def _to_preview_response(preview: ProgramPreview) -> ProgramPreviewValidResponse:
    draft = preview.draft
    return ProgramPreviewValidResponse(
        name=draft.name,
        start_date=draft.start_date,
        tm_auto_update=draft.tm_auto_update,
        design_note=draft.design_note,
        new_exercises=[
            NewExerciseResponse(
                name=exercise.name,
                body_part=exercise.body_part,
                parent_name=exercise.parent_name,
                coefficient=exercise.coefficient,
                increment_kg=exercise.increment_kg,
                default_rest_seconds=exercise.default_rest_seconds,
            )
            for exercise in draft.new_exercises
        ],
        weeks=[
            PreviewWeekResponse(
                week=week.week,
                label=week.label,
                days=[
                    PreviewDayResponse(
                        day=day.day,
                        weekday=day.weekday,
                        exercises=[
                            PreviewPlannedExerciseResponse(
                                exercise_name=planned.planned.exercise_name,
                                is_new_exercise=planned.is_new_exercise,
                                sets=planned.planned.sets,
                                reps=planned.planned.reps,
                                reps_max=planned.planned.reps_max,
                                target_rpe=planned.planned.target_rpe,
                                target_percent=planned.planned.target_percent,
                                target_weight=planned.target_weight,
                            )
                            for planned in day.exercises
                        ],
                    )
                    for day in week.days
                ],
            )
            for week in preview.weeks
        ],
    )
