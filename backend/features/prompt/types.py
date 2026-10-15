from dataclasses import dataclass
from datetime import date

from features.exercise.types import ResolvedExercise, TrainingMaxRecord


@dataclass(frozen=True)
class GenerationPromptSource:
    rules_body: str
    exercises: tuple[ResolvedExercise, ...]
    recent_csv: str
    design_note: str | None


@dataclass(frozen=True)
class ReviewPromptSource:
    from_date: date
    to_date: date
    csv: str
    rules_body: str
    design_note: str | None
    training_max_records: tuple[TrainingMaxRecord, ...]
