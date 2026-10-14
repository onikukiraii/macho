import datetime as dt
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from common.errors import BusinessRuleViolation, Conflict, NotFound
from dependencies import get_exercise_repository, get_program_repository, get_today, get_training_log_repository
from features.exercise.protocol import ExerciseRepository
from features.program.protocol import ProgramRepository
from features.training_log import service
from features.training_log.dto import (
    DayOptionResponse,
    DayOptionsResponse,
    ExerciseHistoryEntryResponse,
    PerformedExerciseCreateParams,
    PerformedExerciseMemoUpdateParams,
    PerformedExerciseReplaceParams,
    PerformedExerciseResponse,
    PlannedResponse,
    PreviousResultResponse,
    ProgramDayProgressResponse,
    ProgramProgressResponse,
    ProgramWeekProgressResponse,
    SetCountResponse,
    SetResponse,
    SetsReplaceParams,
    TopSetResponse,
    TrainingLogCreatedResponse,
    TrainingLogCreateParams,
    TrainingLogDetailResponse,
    TrainingLogSummaryResponse,
    TrainingLogUpdateParams,
    TrainingMaxUpdateResponse,
)
from features.training_log.protocol import TrainingLogRepository
from features.training_log.types import (
    DayOption,
    ExerciseHistoryRecord,
    ExerciseSet,
    PerformedExerciseDetail,
    ProgramProgress,
    TrainingLogCreated,
    TrainingLogDetail,
    TrainingLogSummary,
)

router = APIRouter(prefix="/api/training-logs", tags=["training-logs"])

TrainingLogRepositoryDep = Annotated[TrainingLogRepository, Depends(get_training_log_repository)]
ExerciseRepositoryDep = Annotated[ExerciseRepository, Depends(get_exercise_repository)]
ProgramRepositoryDep = Annotated[ProgramRepository, Depends(get_program_repository)]


@router.get("")
def get_training_logs(
    from_date: dt.date,
    to_date: dt.date,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> list[TrainingLogSummaryResponse]:
    try:
        summaries = service.list_training_logs(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, from_date=from_date, to_date=to_date
        )
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return [_to_summary_response(summary) for summary in summaries]


@router.get("/latest")
def get_latest_training_log(
    repo: TrainingLogRepositoryDep, exercise_repo: ExerciseRepositoryDep, program_repo: ProgramRepositoryDep
) -> TrainingLogSummaryResponse | None:
    summary = service.get_latest_training_log(repo, exercise_repo=exercise_repo, program_repo=program_repo)
    return None if summary is None else _to_summary_response(summary)


@router.get("/day-options")
def get_day_options(repo: TrainingLogRepositoryDep, program_repo: ProgramRepositoryDep) -> DayOptionsResponse:
    options = service.get_day_options(repo, program_repo=program_repo)
    return _to_day_options_response(options)


@router.get("/program-progress")
def get_program_progress(
    repo: TrainingLogRepositoryDep, program_repo: ProgramRepositoryDep
) -> ProgramProgressResponse | None:
    progress = service.get_program_progress(repo, program_repo=program_repo)
    return None if progress is None else _to_progress_response(progress)


@router.get(
    "/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}}},
)
def export_training_logs(
    from_date: dt.date,
    to_date: dt.date,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> Response:
    try:
        csv_text = service.export_training_logs(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, from_date=from_date, to_date=to_date
        )
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return Response(content=csv_text, media_type="text/csv")


@router.get("/export-count")
def get_export_count(from_date: dt.date, to_date: dt.date, repo: TrainingLogRepositoryDep) -> SetCountResponse:
    try:
        count = service.count_export_sets(repo, from_date=from_date, to_date=to_date)
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return SetCountResponse(count=count)


@router.get("/by-exercise/{exercise_uid}")
def get_exercise_history(
    exercise_uid: str,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> list[ExerciseHistoryEntryResponse]:
    try:
        records = service.list_exercise_history(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, exercise_uid=exercise_uid
        )
    except NotFound as e:
        raise HTTPException(404, "種目が見つかりません") from e
    return [_to_history_response(record) for record in records]


@router.post("")
def create_training_log(
    params: TrainingLogCreateParams,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
    today: Annotated[dt.date, Depends(get_today)],
) -> TrainingLogCreatedResponse:
    try:
        created = service.create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=params.date,
            program_day_uid=params.program_day_uid,
            today=today,
        )
    except NotFound as e:
        raise HTTPException(404, "Day が見つかりません") from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return _to_created_response(created)


@router.patch("/exercises/{performed_uid}")
def update_performed_exercise(
    performed_uid: str,
    params: PerformedExerciseReplaceParams | PerformedExerciseMemoUpdateParams,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> TrainingLogDetailResponse:
    try:
        match params:
            case PerformedExerciseReplaceParams():
                detail = service.replace_performed_exercise(
                    repo,
                    exercise_repo=exercise_repo,
                    program_repo=program_repo,
                    performed_uid=performed_uid,
                    exercise_uid=params.exercise_uid,
                )
            case PerformedExerciseMemoUpdateParams():
                detail = service.update_performed_exercise_memo(
                    repo,
                    exercise_repo=exercise_repo,
                    program_repo=program_repo,
                    performed_uid=performed_uid,
                    memo=params.memo,
                )
    except NotFound as e:
        raise HTTPException(404, "種目が見つかりません") from e
    return _to_detail_response(detail)


@router.put("/exercises/{performed_uid}/sets")
def update_sets(
    performed_uid: str,
    params: SetsReplaceParams,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> PerformedExerciseResponse:
    try:
        performed = service.replace_sets(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            performed_uid=performed_uid,
            sets=_to_exercise_sets(params),
        )
    except NotFound as e:
        raise HTTPException(404, "種目が見つかりません") from e
    except Conflict as e:
        raise HTTPException(409, "同じ番号のセットがあります") from e
    return _to_performed_response(performed)


@router.get("/{uid}")
def get_training_log(
    uid: str, repo: TrainingLogRepositoryDep, exercise_repo: ExerciseRepositoryDep, program_repo: ProgramRepositoryDep
) -> TrainingLogDetailResponse:
    try:
        detail = service.get_training_log(repo, exercise_repo=exercise_repo, program_repo=program_repo, uid=uid)
    except NotFound as e:
        raise HTTPException(404, "トレーニング記録が見つかりません") from e
    return _to_detail_response(detail)


@router.patch("/{uid}")
def update_training_log(
    uid: str,
    params: TrainingLogUpdateParams,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> TrainingLogDetailResponse:
    try:
        detail = service.update_training_log_memo(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, uid=uid, memo=params.memo
        )
    except NotFound as e:
        raise HTTPException(404, "トレーニング記録が見つかりません") from e
    return _to_detail_response(detail)


@router.delete("/{uid}", status_code=204)
def delete_training_log(uid: str, repo: TrainingLogRepositoryDep) -> None:
    try:
        service.delete_training_log(repo, uid=uid)
    except NotFound as e:
        raise HTTPException(404, "トレーニング記録が見つかりません") from e


@router.post("/{uid}/exercises")
def create_performed_exercise(
    uid: str,
    params: PerformedExerciseCreateParams,
    repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    program_repo: ProgramRepositoryDep,
) -> TrainingLogDetailResponse:
    try:
        detail = service.add_performed_exercise(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, uid=uid, exercise_uid=params.exercise_uid
        )
    except NotFound as e:
        raise HTTPException(404, "トレーニング記録か種目が見つかりません") from e
    return _to_detail_response(detail)


def _to_exercise_sets(params: SetsReplaceParams) -> list[ExerciseSet]:
    return [
        ExerciseSet(order=params_set.order, weight=params_set.weight, reps=params_set.reps, rir=params_set.rir)
        for params_set in params.sets
    ]


def _to_day_options_response(options: Sequence[DayOption]) -> DayOptionsResponse:
    return DayOptionsResponse(
        options=[
            DayOptionResponse(
                program_day_uid=option.scheduled_day.day.uid,
                week=option.scheduled_day.week.week,
                week_label=option.scheduled_day.week.label,
                day=option.scheduled_day.day.day,
                weekday=option.scheduled_day.day.weekday,
                guide_date=option.scheduled_day.guide_date,
                is_next=option.is_next,
                last_recorded_on=option.last_recorded_on,
            )
            for option in options
        ]
    )


def _to_created_response(created: TrainingLogCreated) -> TrainingLogCreatedResponse:
    return TrainingLogCreatedResponse(
        uid=created.training_log.uid,
        training_max_updates=[
            TrainingMaxUpdateResponse(exercise_name=update.exercise_name, before=update.before, after=update.after)
            for update in created.training_max_updates
        ],
    )


def _to_set_response(exercise_set: ExerciseSet) -> SetResponse:
    return SetResponse(
        order=exercise_set.order, weight=exercise_set.weight, reps=exercise_set.reps, rir=exercise_set.rir
    )


def _to_summary_response(summary: TrainingLogSummary) -> TrainingLogSummaryResponse:
    return TrainingLogSummaryResponse(
        uid=summary.training_log.uid,
        date=summary.training_log.date,
        day_label=service.format_scheduled_day_label(summary.scheduled_day),
        week_label=None if summary.scheduled_day is None else summary.scheduled_day.week.label,
        top_sets=[
            TopSetResponse(
                exercise_name=top_set.exercise_name,
                weight=top_set.exercise_set.weight,
                reps=top_set.exercise_set.reps,
                rir=top_set.exercise_set.rir,
            )
            for top_set in summary.top_sets
        ],
        body_parts=list(summary.body_parts),
    )


def _to_performed_response(detail: PerformedExerciseDetail) -> PerformedExerciseResponse:
    planned = detail.planned
    previous = detail.previous
    return PerformedExerciseResponse(
        uid=detail.performed.uid,
        exercise_uid=detail.exercise.uid,
        exercise_name=detail.exercise.name,
        planned=None
        if planned is None
        else PlannedResponse(
            sets=planned.sets,
            reps=planned.reps,
            reps_max=planned.reps_max,
            target_rpe=planned.target_rpe,
            target_percent=planned.target_percent,
        ),
        target_weight=detail.target_weight,
        previous=None
        if previous is None
        else PreviousResultResponse(
            date=previous.date,
            top_set=_to_set_response(previous.top_set),
            sets=[_to_set_response(exercise_set) for exercise_set in previous.sets],
        ),
        default_rest_seconds=detail.exercise.default_rest_seconds,
        memo=detail.performed.memo,
        sets=[_to_set_response(exercise_set) for exercise_set in detail.performed.sets],
    )


def _to_detail_response(detail: TrainingLogDetail) -> TrainingLogDetailResponse:
    scheduled_day = detail.scheduled_day
    return TrainingLogDetailResponse(
        uid=detail.training_log.uid,
        date=detail.training_log.date,
        day_label=service.format_scheduled_day_label(scheduled_day),
        week_label=None if scheduled_day is None else scheduled_day.week.label,
        guide_date=None if scheduled_day is None else scheduled_day.guide_date,
        memo=detail.training_log.memo,
        exercises=[_to_performed_response(performed) for performed in detail.exercises],
    )


def _to_history_response(record: ExerciseHistoryRecord) -> ExerciseHistoryEntryResponse:
    return ExerciseHistoryEntryResponse(
        training_log_uid=record.entry.training_log_uid,
        date=record.entry.date,
        day_label=service.format_scheduled_day_label(record.scheduled_day),
        sets=[_to_set_response(exercise_set) for exercise_set in record.entry.sets],
    )


def _to_progress_response(progress: ProgramProgress) -> ProgramProgressResponse:
    program = progress.program
    return ProgramProgressResponse(
        name=program.name,
        start_date=program.start_date,
        week_count=len(program.weeks),
        tm_auto_update=program.tm_auto_update,
        design_note=program.design_note,
        weeks=[
            ProgramWeekProgressResponse(
                week=week.week,
                label=week.label,
                days=[
                    ProgramDayProgressResponse(
                        program_day_uid=day.uid,
                        day=day.day,
                        weekday=day.weekday,
                        status=progress.day_statuses[day.id],
                    )
                    for day in week.days
                ],
            )
            for week in program.weeks
        ],
    )
