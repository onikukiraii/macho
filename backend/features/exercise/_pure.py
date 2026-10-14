from collections.abc import Sequence
from datetime import date, tzinfo

from common.errors import BusinessRuleViolation
from features.exercise.types import (
    BodyPart,
    CalculationBasis,
    Exercise,
    ExerciseFields,
    ExerciseKind,
    ResolvedExercise,
    TrainingMax,
)


def classify_exercise(exercise: Exercise, *, has_training_max: bool) -> ExerciseKind:
    if exercise.parent_id is not None:
        return ExerciseKind.derived
    if has_training_max:
        return ExerciseKind.training_max
    return ExerciseKind.double_progression


def validate_derivation(
    *,
    exercise_id: int | None,
    parent: Exercise | None,
    has_derived_exercises: bool,
    has_training_max: bool,
    coefficient: float | None,
    e1rm_divisor: float | None,
) -> None:
    if parent is None:
        if e1rm_divisor is None:
            raise BusinessRuleViolation("派生元が無い種目には分母を入力してください")
        return
    if parent.id == exercise_id:
        raise BusinessRuleViolation("種目自身は派生元に選択できません")
    if parent.parent_id is not None:
        raise BusinessRuleViolation("派生種目は派生元に選択できません")
    if has_derived_exercises:
        raise BusinessRuleViolation("派生種目を持つ種目は派生種目にできません")
    if has_training_max:
        raise BusinessRuleViolation("トレーニングマックスの履歴がある種目は派生種目にできません")
    if coefficient is None:
        raise BusinessRuleViolation("派生種目には換算係数を入力してください")


def has_derived_exercises(exercise: Exercise, exercises: Sequence[Exercise]) -> bool:
    return any(candidate.parent_id == exercise.id for candidate in exercises)


def has_training_max_history(training_maxes: Sequence[TrainingMax], *, exercise_id: int) -> bool:
    return len(list_training_max_history(training_maxes, exercise_id=exercise_id)) > 0


def validate_training_max_owner(exercise: Exercise) -> None:
    if exercise.parent_id is not None:
        raise BusinessRuleViolation("派生種目にはトレーニングマックスを登録できません")


def build_exercise_fields(
    *,
    name: str,
    body_part: BodyPart,
    parent: Exercise | None,
    coefficient: float | None,
    e1rm_divisor: float | None,
    increment_kg: float,
    default_rest_seconds: int,
) -> ExerciseFields:
    is_derived = parent is not None
    return ExerciseFields(
        name=name,
        body_part=body_part,
        parent_id=parent.id if parent is not None else None,
        coefficient=coefficient if is_derived else None,
        e1rm_divisor=None if is_derived else e1rm_divisor,
        increment_kg=increment_kg,
        default_rest_seconds=default_rest_seconds,
    )


def list_training_max_history(training_maxes: Sequence[TrainingMax], *, exercise_id: int) -> tuple[TrainingMax, ...]:
    return tuple(training_max for training_max in training_maxes if training_max.exercise_id == exercise_id)


def select_training_max(newest_first: Sequence[TrainingMax], *, on: date, timezone: tzinfo) -> float | None:
    for training_max in newest_first:
        if training_max.effective_at.astimezone(timezone).date() <= on:
            return training_max.value
    return None


def resolve_exercise(
    exercise: Exercise, *, exercises: Sequence[Exercise], training_maxes: Sequence[TrainingMax]
) -> ResolvedExercise:
    parent = _find_parent(exercise, exercises)
    history = list_training_max_history(training_maxes, exercise_id=exercise.id)
    return ResolvedExercise(
        exercise=exercise,
        kind=classify_exercise(exercise, has_training_max=len(history) > 0),
        parent=parent,
        e1rm_divisor=_resolve_e1rm_divisor(exercise, parent=parent),
        current_training_max=history[0].value if len(history) > 0 else None,
    )


def build_calculation_basis(
    exercise: Exercise,
    *,
    exercises: Sequence[Exercise],
    training_maxes: Sequence[TrainingMax],
    on: date,
    timezone: tzinfo,
) -> CalculationBasis:
    parent = _find_parent(exercise, exercises)
    owner = parent if parent is not None else exercise
    owner_history = list_training_max_history(training_maxes, exercise_id=owner.id)
    has_tm_owner = parent is not None or len(owner_history) > 0
    return CalculationBasis(
        exercise_id=exercise.id,
        name=exercise.name,
        tm_owner_id=owner.id if has_tm_owner else None,
        coefficient=_resolve_coefficient(exercise),
        e1rm_divisor=_resolve_e1rm_divisor(exercise, parent=parent),
        increment_kg=exercise.increment_kg,
        training_max=select_training_max(owner_history, on=on, timezone=timezone),
    )


def _find_parent(exercise: Exercise, exercises: Sequence[Exercise]) -> Exercise | None:
    if exercise.parent_id is None:
        return None
    return next(candidate for candidate in exercises if candidate.id == exercise.parent_id)


def _resolve_coefficient(exercise: Exercise) -> float:
    if exercise.parent_id is None:
        return 1.0
    if exercise.coefficient is None:
        raise ValueError(f"換算係数の無い派生種目があります: uid={exercise.uid}")
    return exercise.coefficient


def _resolve_e1rm_divisor(exercise: Exercise, *, parent: Exercise | None) -> float:
    owner = parent if parent is not None else exercise
    if owner.e1rm_divisor is None:
        raise ValueError(f"分母の無い種目があります: uid={owner.uid}")
    return owner.e1rm_divisor
