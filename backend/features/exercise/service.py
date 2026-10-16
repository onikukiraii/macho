from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from common.config import settings
from features.exercise._pure import (
    build_calculation_basis,
    build_exercise_fields,
    has_derived_exercises,
    has_training_max_history,
    list_training_max_history,
    resolve_exercise,
    validate_derivation,
    validate_training_max_owner,
)
from features.exercise.protocol import ExerciseRepository
from features.exercise.types import (
    BodyPart,
    CalculationBasis,
    Exercise,
    ExerciseDetail,
    ResolvedExercise,
    TrainingMax,
    TrainingMaxRecord,
    TrainingMaxSource,
    TrainingMaxUpdate,
)


def list_exercises(repo: ExerciseRepository) -> list[ResolvedExercise]:
    exercises = repo.list_all()
    training_maxes = repo.list_training_maxes()
    return [resolve_exercise(exercise, exercises=exercises, training_maxes=training_maxes) for exercise in exercises]


def get_exercise(repo: ExerciseRepository, *, uid: str) -> ExerciseDetail:
    return _build_detail(repo, repo.get(uid))


def create_exercise(
    repo: ExerciseRepository,
    *,
    name: str,
    body_part: BodyPart,
    parent_uid: str | None,
    coefficient: float | None,
    e1rm_divisor: float | None,
    increment_kg: float,
    default_rest_seconds: int,
) -> ResolvedExercise:
    parent = _get_parent(repo, parent_uid)
    validate_derivation(
        exercise_id=None,
        parent=parent,
        has_derived_exercises=False,
        has_training_max=False,
        coefficient=coefficient,
        e1rm_divisor=e1rm_divisor,
    )
    fields = build_exercise_fields(
        name=name,
        body_part=body_part,
        parent=parent,
        coefficient=coefficient,
        e1rm_divisor=e1rm_divisor,
        increment_kg=increment_kg,
        default_rest_seconds=default_rest_seconds,
    )
    exercise = repo.create(uid=str(uuid4()), fields=fields)
    return resolve_exercise(exercise, exercises=repo.list_all(), training_maxes=repo.list_training_maxes())


def update_exercise(
    repo: ExerciseRepository,
    *,
    uid: str,
    name: str,
    body_part: BodyPart,
    parent_uid: str | None,
    coefficient: float | None,
    e1rm_divisor: float | None,
    increment_kg: float,
    default_rest_seconds: int,
) -> ResolvedExercise:
    exercise = repo.get(uid)
    parent = _get_parent(repo, parent_uid)
    exercises = repo.list_all()
    training_maxes = repo.list_training_maxes()
    validate_derivation(
        exercise_id=exercise.id,
        parent=parent,
        has_derived_exercises=has_derived_exercises(exercise, exercises),
        has_training_max=has_training_max_history(training_maxes, exercise_id=exercise.id),
        coefficient=coefficient,
        e1rm_divisor=e1rm_divisor,
    )
    fields = build_exercise_fields(
        name=name,
        body_part=body_part,
        parent=parent,
        coefficient=coefficient,
        e1rm_divisor=e1rm_divisor,
        increment_kg=increment_kg,
        default_rest_seconds=default_rest_seconds,
    )
    updated = repo.update(uid, fields=fields)
    return resolve_exercise(updated, exercises=repo.list_all(), training_maxes=training_maxes)


def add_training_max(repo: ExerciseRepository, *, uid: str, value: float, reason: str) -> ExerciseDetail:
    exercise = repo.get(uid)
    validate_training_max_owner(exercise)
    repo.add_training_max(
        TrainingMax(
            exercise_id=exercise.id,
            value=value,
            effective_at=datetime.now(UTC),
            source=TrainingMaxSource.manual,
            reason=reason,
        )
    )
    return _build_detail(repo, exercise)


def list_training_max_records(repo: ExerciseRepository) -> list[TrainingMaxRecord]:
    names = {exercise.id: exercise.name for exercise in repo.list_all()}
    return [
        TrainingMaxRecord(exercise_name=names[training_max.exercise_id], training_max=training_max)
        for training_max in sorted(repo.list_training_maxes(), key=lambda training_max: training_max.effective_at)
    ]


def get_calculation_bases(repo: ExerciseRepository, *, on: date) -> dict[int, CalculationBasis]:
    exercises = repo.list_all()
    training_maxes = repo.list_training_maxes()
    timezone = ZoneInfo(settings.app_timezone)
    return {
        exercise.id: build_calculation_basis(
            exercise, exercises=exercises, training_maxes=training_maxes, on=on, timezone=timezone
        )
        for exercise in exercises
    }


def is_week_evaluated(repo: ExerciseRepository, *, week_start: date) -> bool:
    return repo.is_week_evaluated(week_start)


def record_weekly_evaluation(
    repo: ExerciseRepository, *, week_start: date, effective_at: datetime, updates: Sequence[TrainingMaxUpdate]
) -> None:
    repo.save_weekly_evaluation(
        week_start=week_start,
        training_maxes=[
            TrainingMax(
                exercise_id=update.exercise_id,
                value=update.after,
                effective_at=effective_at,
                source=TrainingMaxSource.auto,
                reason=update.reason,
            )
            for update in updates
        ],
    )


def _get_parent(repo: ExerciseRepository, parent_uid: str | None) -> Exercise | None:
    if parent_uid is None:
        return None
    return repo.get(parent_uid)


def _build_detail(repo: ExerciseRepository, exercise: Exercise) -> ExerciseDetail:
    training_maxes = repo.list_training_maxes()
    return ExerciseDetail(
        exercise=resolve_exercise(exercise, exercises=repo.list_all(), training_maxes=training_maxes),
        training_max_history=list_training_max_history(training_maxes, exercise_id=exercise.id),
    )
