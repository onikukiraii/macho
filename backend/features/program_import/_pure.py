from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import date

from features.exercise.types import CalculationBasis, Exercise
from features.program.types import NewPlannedExercise, NewProgram, NewProgramDay, NewProgramWeek
from features.program_import.types import (
    DraftExercise,
    DraftIssue,
    DraftPlannedExercise,
    PreviewDay,
    PreviewPlannedExercise,
    PreviewWeek,
    ProgramDraft,
    ProgramPreview,
)

UNKNOWN_EXERCISE_MESSAGE = "種目一覧にも new_exercises にもない種目です"
BOTH_TARGETS_MESSAGE = "target_rpe と target_percent の両方が設定されています。どちらか一方にしてください"
MISSING_TARGET_MESSAGE = "トレーニングマックスを使う種目です。target_rpe か target_percent を設定してください"
UNEXPECTED_TARGET_MESSAGE = "トレーニングマックスを使わない種目には target_rpe と target_percent を設定できません"
UNEXPECTED_REPS_MAX_MESSAGE = "トレーニングマックスを使う種目には reps_max を設定できません"
DUPLICATE_WEEK_MESSAGE = "week が重複しています"
DUPLICATE_DAY_MESSAGE = "週の中で day が重複しています"
EXISTING_EXERCISE_NAME_MESSAGE = "同じ名前の種目がすでにあります"
DUPLICATE_NEW_EXERCISE_MESSAGE = "new_exercises の中で名前が重複しています"
UNKNOWN_PARENT_MESSAGE = "parent の種目が種目一覧にありません"
DERIVED_PARENT_MESSAGE = "派生種目は parent に指定できません"
MISSING_DIVISOR_MESSAGE = "parent が無い種目には e1rm_divisor を設定してください"
MISSING_COEFFICIENT_MESSAGE = "parent がある種目には coefficient を設定してください"
START_DATE_AFTER_TODAY_MESSAGE = "今日より後の日付は指定できません。開始日になってから取り込んでください"
START_DATE_NOT_AFTER_LAST_RECORD_MESSAGE = "最後のトレーニング記録の日付より後の日付にしてください"
REPS_MAX_BELOW_REPS_MESSAGE = "reps_max は reps 以上にしてください"
START_DATE_NOT_AFTER_CURRENT_MESSAGE = "進行中のプログラムの開始日より後の日付にしてください"

WeightCalculator = Callable[[CalculationBasis, DraftPlannedExercise], float | None]


def validate_draft(
    draft: ProgramDraft,
    *,
    exercises: Sequence[Exercise],
    bases: Mapping[int, CalculationBasis],
    current_start_date: date | None,
    last_recorded_on: date | None,
    today: date,
) -> list[DraftIssue]:
    existing_by_name = {exercise.name: exercise for exercise in exercises}
    issues: list[DraftIssue] = []
    if draft.start_date > today:
        issues.append(DraftIssue(location="start_date", message=START_DATE_AFTER_TODAY_MESSAGE))
    if last_recorded_on is not None and draft.start_date <= last_recorded_on:
        issues.append(DraftIssue(location="start_date", message=START_DATE_NOT_AFTER_LAST_RECORD_MESSAGE))
    if current_start_date is not None and draft.start_date <= current_start_date:
        issues.append(DraftIssue(location="start_date", message=START_DATE_NOT_AFTER_CURRENT_MESSAGE))
    issues.extend(_validate_new_exercises(draft.new_exercises, existing_by_name=existing_by_name))
    known_names = set(existing_by_name) | {exercise.name for exercise in draft.new_exercises}
    training_max_names = _list_training_max_exercise_names(draft, exercises=exercises, bases=bases)
    seen_weeks: set[int] = set()
    for week in draft.weeks:
        if week.week in seen_weeks:
            issues.append(DraftIssue(location=f"第{week.week}週", message=DUPLICATE_WEEK_MESSAGE))
        seen_weeks.add(week.week)
        seen_days: set[int] = set()
        for day in week.days:
            day_location = f"第{week.week}週 Day {day.day}"
            if day.day in seen_days:
                issues.append(DraftIssue(location=day_location, message=DUPLICATE_DAY_MESSAGE))
            seen_days.add(day.day)
            for planned in day.exercises:
                issues.extend(
                    DraftIssue(location=f"{day_location}「{planned.exercise_name}」", message=message)
                    for message in _validate_planned(
                        planned, known_names=known_names, training_max_names=training_max_names
                    )
                )
    return issues


def build_preview_bases(
    draft: ProgramDraft, *, exercises: Sequence[Exercise], bases: Mapping[int, CalculationBasis]
) -> dict[str, CalculationBasis]:
    existing_by_name = {exercise.name: exercise for exercise in exercises}
    preview_bases = {
        exercise.name: bases[exercise.id] for exercise in exercises if bases[exercise.id].tm_owner_id is not None
    }
    for new_exercise in draft.new_exercises:
        if new_exercise.parent_name is None or new_exercise.coefficient is None:
            continue
        parent = existing_by_name[new_exercise.parent_name]
        preview_bases[new_exercise.name] = replace(
            bases[parent.id],
            name=new_exercise.name,
            tm_owner_id=parent.id,
            coefficient=new_exercise.coefficient,
            increment_kg=new_exercise.increment_kg,
        )
    return preview_bases


def build_preview(
    draft: ProgramDraft, *, preview_bases: Mapping[str, CalculationBasis], calculate_weight: WeightCalculator
) -> ProgramPreview:
    new_names = {exercise.name for exercise in draft.new_exercises}
    return ProgramPreview(
        draft=draft,
        weeks=tuple(
            PreviewWeek(
                week=week.week,
                label=week.label,
                days=tuple(
                    PreviewDay(
                        day=day.day,
                        weekday=day.weekday,
                        exercises=tuple(
                            PreviewPlannedExercise(
                                planned=planned,
                                is_new_exercise=planned.exercise_name in new_names,
                                target_weight=_preview_weight(
                                    planned, preview_bases=preview_bases, calculate_weight=calculate_weight
                                ),
                            )
                            for planned in day.exercises
                        ),
                    )
                    for day in sorted(week.days, key=lambda day: day.day)
                ),
            )
            for week in sorted(draft.weeks, key=lambda week: week.week)
        ),
    )


def build_new_program(draft: ProgramDraft, *, exercise_ids: Mapping[str, int]) -> NewProgram:
    return NewProgram(
        name=draft.name,
        start_date=draft.start_date,
        tm_auto_update=draft.tm_auto_update,
        design_note=draft.design_note,
        weeks=tuple(
            NewProgramWeek(
                week=week.week,
                label=week.label,
                days=tuple(
                    NewProgramDay(
                        day=day.day,
                        weekday=day.weekday,
                        planned_exercises=tuple(
                            NewPlannedExercise(
                                exercise_id=exercise_ids[planned.exercise_name],
                                order=order,
                                sets=planned.sets,
                                reps=planned.reps,
                                reps_max=planned.reps_max,
                                target_rpe=planned.target_rpe,
                                target_percent=planned.target_percent,
                            )
                            for order, planned in enumerate(day.exercises, start=1)
                        ),
                    )
                    for day in week.days
                ),
            )
            for week in draft.weeks
        ),
    )


def _validate_new_exercises(
    new_exercises: Sequence[DraftExercise], *, existing_by_name: Mapping[str, Exercise]
) -> list[DraftIssue]:
    issues: list[DraftIssue] = []
    seen_names: set[str] = set()
    for new_exercise in new_exercises:
        location = f"new_exercises「{new_exercise.name}」"
        if new_exercise.name in existing_by_name:
            issues.append(DraftIssue(location=location, message=EXISTING_EXERCISE_NAME_MESSAGE))
        elif new_exercise.name in seen_names:
            issues.append(DraftIssue(location=location, message=DUPLICATE_NEW_EXERCISE_MESSAGE))
        seen_names.add(new_exercise.name)
        message = _validate_derivation(new_exercise, existing_by_name=existing_by_name)
        if message is not None:
            issues.append(DraftIssue(location=location, message=message))
    return issues


def _validate_derivation(new_exercise: DraftExercise, *, existing_by_name: Mapping[str, Exercise]) -> str | None:
    if new_exercise.parent_name is None:
        return MISSING_DIVISOR_MESSAGE if new_exercise.e1rm_divisor is None else None
    parent = existing_by_name.get(new_exercise.parent_name)
    if parent is None:
        return UNKNOWN_PARENT_MESSAGE
    if parent.parent_id is not None:
        return DERIVED_PARENT_MESSAGE
    if new_exercise.coefficient is None:
        return MISSING_COEFFICIENT_MESSAGE
    return None


def _list_training_max_exercise_names(
    draft: ProgramDraft, *, exercises: Sequence[Exercise], bases: Mapping[int, CalculationBasis]
) -> set[str]:
    existing = {exercise.name for exercise in exercises if bases[exercise.id].tm_owner_id is not None}
    derived_new = {exercise.name for exercise in draft.new_exercises if exercise.parent_name is not None}
    return existing | derived_new


def _validate_planned(
    planned: DraftPlannedExercise, *, known_names: set[str], training_max_names: set[str]
) -> list[str]:
    if planned.exercise_name not in known_names:
        return [UNKNOWN_EXERCISE_MESSAGE]
    has_rpe = planned.target_rpe is not None
    has_percent = planned.target_percent is not None
    if planned.exercise_name not in training_max_names:
        double_progression_messages = [UNEXPECTED_TARGET_MESSAGE] if has_rpe or has_percent else []
        if planned.reps_max is not None and planned.reps_max < planned.reps:
            double_progression_messages.append(REPS_MAX_BELOW_REPS_MESSAGE)
        return double_progression_messages
    messages: list[str] = []
    if has_rpe and has_percent:
        messages.append(BOTH_TARGETS_MESSAGE)
    if not has_rpe and not has_percent:
        messages.append(MISSING_TARGET_MESSAGE)
    if planned.reps_max is not None:
        messages.append(UNEXPECTED_REPS_MAX_MESSAGE)
    return messages


def _preview_weight(
    planned: DraftPlannedExercise,
    *,
    preview_bases: Mapping[str, CalculationBasis],
    calculate_weight: WeightCalculator,
) -> float | None:
    basis = preview_bases.get(planned.exercise_name)
    if basis is None:
        return None
    return calculate_weight(basis, planned)
