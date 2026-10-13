from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import BusinessRuleViolation, Conflict, NotFound
from dependencies import get_exercise_repository
from features.exercise import service
from features.exercise.dto import (
    ExerciseDetailResponse,
    ExerciseResponse,
    ExerciseSaveParams,
    TrainingMaxCreateParams,
    TrainingMaxResponse,
)
from features.exercise.protocol import ExerciseRepository
from features.exercise.types import ExerciseDetail, ResolvedExercise

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
def get_exercises(repo: Annotated[ExerciseRepository, Depends(get_exercise_repository)]) -> list[ExerciseResponse]:
    return [_to_response(exercise) for exercise in service.list_exercises(repo)]


@router.get("/{uid}")
def get_exercise(
    uid: str, repo: Annotated[ExerciseRepository, Depends(get_exercise_repository)]
) -> ExerciseDetailResponse:
    try:
        detail = service.get_exercise(repo, uid=uid)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    return _to_detail_response(detail)


@router.post("")
def create_exercise(
    params: ExerciseSaveParams, repo: Annotated[ExerciseRepository, Depends(get_exercise_repository)]
) -> ExerciseResponse:
    try:
        exercise = service.create_exercise(
            repo,
            name=params.name,
            parent_uid=params.parent_uid,
            coefficient=params.coefficient,
            e1rm_divisor=params.e1rm_divisor,
            increment_kg=params.increment_kg,
            default_rest_seconds=params.default_rest_seconds,
        )
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    except Conflict as e:
        raise HTTPException(409, str(e)) from e
    return _to_response(exercise)


@router.put("/{uid}")
def update_exercise(
    uid: str,
    params: ExerciseSaveParams,
    repo: Annotated[ExerciseRepository, Depends(get_exercise_repository)],
) -> ExerciseResponse:
    try:
        exercise = service.update_exercise(
            repo,
            uid=uid,
            name=params.name,
            parent_uid=params.parent_uid,
            coefficient=params.coefficient,
            e1rm_divisor=params.e1rm_divisor,
            increment_kg=params.increment_kg,
            default_rest_seconds=params.default_rest_seconds,
        )
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    except Conflict as e:
        raise HTTPException(409, str(e)) from e
    return _to_response(exercise)


@router.post("/{uid}/training-maxes")
def create_training_max(
    uid: str,
    params: TrainingMaxCreateParams,
    repo: Annotated[ExerciseRepository, Depends(get_exercise_repository)],
) -> ExerciseDetailResponse:
    try:
        detail = service.change_training_max(repo, uid=uid, value=params.value, reason=params.reason)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return _to_detail_response(detail)


def _to_response(resolved: ResolvedExercise) -> ExerciseResponse:
    return ExerciseResponse(
        uid=resolved.exercise.uid,
        name=resolved.exercise.name,
        kind=resolved.kind,
        parent_uid=resolved.parent.uid if resolved.parent is not None else None,
        parent_name=resolved.parent.name if resolved.parent is not None else None,
        coefficient=resolved.exercise.coefficient,
        e1rm_divisor=resolved.e1rm_divisor,
        increment_kg=resolved.exercise.increment_kg,
        default_rest_seconds=resolved.exercise.default_rest_seconds,
        current_training_max=resolved.current_training_max,
    )


def _to_detail_response(detail: ExerciseDetail) -> ExerciseDetailResponse:
    return ExerciseDetailResponse(
        exercise=_to_response(detail.exercise),
        training_max_history=[
            TrainingMaxResponse(
                value=training_max.value,
                effective_at=training_max.effective_at,
                source=training_max.source,
                reason=training_max.reason,
            )
            for training_max in detail.training_max_history
        ],
    )
