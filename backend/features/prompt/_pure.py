from datetime import date, tzinfo

from features.exercise.types import BodyPart, ExerciseKind, ResolvedExercise, TrainingMaxRecord
from features.prompt.prompts import (
    DESIGN_NOTE_SECTION_TEMPLATE,
    GENERATION_PROMPT_TEMPLATE,
    JSON_EXAMPLE,
    REVIEW_PROMPT_TEMPLATE,
)
from features.prompt.types import GenerationPromptSource, ReviewPromptSource

_BODY_PART_LABELS = {
    BodyPart.chest: "胸",
    BodyPart.back: "背中",
    BodyPart.shoulders: "肩",
    BodyPart.arms: "腕",
    BodyPart.legs: "脚",
    BodyPart.abs: "腹",
}


def build_generation_prompt(source: GenerationPromptSource) -> str:
    return GENERATION_PROMPT_TEMPLATE.format(
        rules_body=source.rules_body,
        exercise_lines="\n".join(_format_exercise(resolved) for resolved in source.exercises),
        recent_csv=source.recent_csv,
        design_note_section=_format_design_note_section(source.design_note),
        json_example=JSON_EXAMPLE,
    )


def build_review_prompt(source: ReviewPromptSource, *, timezone: tzinfo) -> str:
    return REVIEW_PROMPT_TEMPLATE.format(
        from_date=_format_date(source.from_date),
        to_date=_format_date(source.to_date),
        csv=source.csv,
        rules_body=source.rules_body,
        design_note_section=_format_design_note_section(source.design_note),
        training_max_lines="\n".join(
            _format_training_max_record(record, timezone=timezone) for record in source.training_max_records
        ),
    )


def _format_exercise(resolved: ResolvedExercise) -> str:
    exercise = resolved.exercise
    common = f"上げる幅 {exercise.increment_kg:g} kg、レスト {exercise.default_rest_seconds} 秒"
    body_part = _BODY_PART_LABELS[exercise.body_part]
    match resolved.kind:
        case ExerciseKind.derived:
            parent_name = "" if resolved.parent is None else resolved.parent.name
            return f"- {exercise.name}: {body_part}、{parent_name}の派生種目 × {exercise.coefficient:g}、{common}"
        case ExerciseKind.training_max:
            return (
                f"- {exercise.name}: {body_part}、トレーニングマックス {resolved.current_training_max:g} kg、"
                f"分母 {resolved.e1rm_divisor:g}、{common}"
            )
        case ExerciseKind.double_progression:
            return f"- {exercise.name}: {body_part}、ダブルプログレッション、分母 {resolved.e1rm_divisor:g}、{common}"


def _format_design_note_section(design_note: str | None) -> str:
    if design_note is None:
        return ""
    return DESIGN_NOTE_SECTION_TEMPLATE.format(design_note=design_note)


def _format_training_max_record(record: TrainingMaxRecord, *, timezone: tzinfo) -> str:
    training_max = record.training_max
    effective_on = training_max.effective_at.astimezone(timezone).date()
    return f"- {_format_date(effective_on)} {record.exercise_name} {training_max.value:g} kg: {training_max.reason}"


def _format_date(on: date) -> str:
    return on.strftime("%Y/%m/%d")
