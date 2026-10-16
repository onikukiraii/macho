from datetime import date

from common.errors import BusinessRuleViolation
from features.exercise import service as exercise_service
from features.exercise.protocol import ExerciseRepository
from features.exercise.types import CalculationBasis, Exercise
from features.program import service as program_service
from features.program.protocol import ProgramRepository
from features.program.types import Program
from features.program_import import _pure
from features.program_import.types import DraftIssue, DraftPlannedExercise, DraftRejected, ProgramDraft, ProgramPreview
from features.training_log import service as training_log_service
from features.training_log.protocol import TrainingLogRepository


def preview_program(
    *,
    program_repo: ProgramRepository,
    exercise_repo: ExerciseRepository,
    training_log_repo: TrainingLogRepository,
    draft: ProgramDraft,
    today: date,
) -> ProgramPreview | DraftRejected:
    exercises = _list_exercises(exercise_repo)
    bases = exercise_service.get_calculation_bases(exercise_repo, on=today)
    issues = _validate(program_repo, training_log_repo, draft=draft, exercises=exercises, bases=bases, today=today)
    if len(issues) > 0:
        return DraftRejected(issues=tuple(issues))
    return _pure.build_preview(
        draft,
        preview_bases=_pure.build_preview_bases(draft, exercises=exercises, bases=bases),
        calculate_weight=_calculate_weight,
    )


def import_program(
    *,
    program_repo: ProgramRepository,
    exercise_repo: ExerciseRepository,
    training_log_repo: TrainingLogRepository,
    draft: ProgramDraft,
    today: date,
) -> Program:
    exercises = _list_exercises(exercise_repo)
    bases = exercise_service.get_calculation_bases(exercise_repo, on=today)
    issues = _validate(program_repo, training_log_repo, draft=draft, exercises=exercises, bases=bases, today=today)
    if len(issues) > 0:
        raise BusinessRuleViolation(f"プログラムの JSON に {len(issues)} 件のエラーがあります: name={draft.name}")
    existing_by_name = {exercise.name: exercise for exercise in exercises}
    exercise_ids = {exercise.name: exercise.id for exercise in exercises}
    # ponytail: 種目の作成とプログラムの作成は別々に commit する。検証を書き込みの前に終えているので、
    # 途中で失敗するのは DB の障害に限る。種目だけが残ったときは、JSON の new_exercises から外して取り込み直す
    for new_exercise in draft.new_exercises:
        created = exercise_service.create_exercise(
            exercise_repo,
            name=new_exercise.name,
            body_part=new_exercise.body_part,
            parent_uid=None if new_exercise.parent_name is None else existing_by_name[new_exercise.parent_name].uid,
            coefficient=new_exercise.coefficient,
            e1rm_divisor=new_exercise.e1rm_divisor,
            increment_kg=new_exercise.increment_kg,
            default_rest_seconds=new_exercise.default_rest_seconds,
        )
        exercise_ids[new_exercise.name] = created.exercise.id
    return program_service.create_program(
        program_repo, program=_pure.build_new_program(draft, exercise_ids=exercise_ids)
    )


def _list_exercises(exercise_repo: ExerciseRepository) -> list[Exercise]:
    return [resolved.exercise for resolved in exercise_service.list_exercises(exercise_repo)]


def _validate(
    program_repo: ProgramRepository,
    training_log_repo: TrainingLogRepository,
    *,
    draft: ProgramDraft,
    exercises: list[Exercise],
    bases: dict[int, CalculationBasis],
    today: date,
) -> list[DraftIssue]:
    current = program_service.get_current_program(program_repo)
    return _pure.validate_draft(
        draft,
        exercises=exercises,
        bases=bases,
        current_start_date=None if current is None else current.start_date,
        last_recorded_on=training_log_service.get_latest_recorded_date(training_log_repo),
        today=today,
    )


def _calculate_weight(basis: CalculationBasis, planned: DraftPlannedExercise) -> float | None:
    return training_log_service.calculate_training_max_weight(
        basis, reps=planned.reps, target_rpe=planned.target_rpe, target_percent=planned.target_percent
    )
