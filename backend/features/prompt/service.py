from datetime import date, timedelta
from zoneinfo import ZoneInfo

from common.config import settings
from features.exercise import service as exercise_service
from features.exercise.protocol import ExerciseRepository
from features.program import service as program_service
from features.program.protocol import ProgramRepository, ProgramRulesRepository
from features.prompt import _pure
from features.prompt.types import GenerationPromptSource, ReviewPromptSource
from features.training_log import service as training_log_service
from features.training_log.protocol import TrainingLogRepository

RECENT_RESULT_DAYS = 28


def get_generation_prompt(
    *,
    program_repo: ProgramRepository,
    rules_repo: ProgramRulesRepository,
    exercise_repo: ExerciseRepository,
    training_log_repo: TrainingLogRepository,
    today: date,
) -> str:
    current = program_service.get_current_program(program_repo)
    recent_csv = training_log_service.export_training_logs(
        training_log_repo,
        exercise_repo=exercise_repo,
        program_repo=program_repo,
        from_date=today - timedelta(days=RECENT_RESULT_DAYS - 1),
        to_date=today,
    )
    return _pure.build_generation_prompt(
        GenerationPromptSource(
            rules_body=program_service.get_program_rules(rules_repo).body,
            exercises=tuple(exercise_service.list_exercises(exercise_repo)),
            recent_csv=recent_csv,
            design_note=None if current is None else current.design_note,
        )
    )


def get_review_prompt(
    *,
    program_repo: ProgramRepository,
    rules_repo: ProgramRulesRepository,
    exercise_repo: ExerciseRepository,
    training_log_repo: TrainingLogRepository,
    from_date: date,
    to_date: date,
) -> str:
    csv = training_log_service.export_training_logs(
        training_log_repo, exercise_repo=exercise_repo, program_repo=program_repo, from_date=from_date, to_date=to_date
    )
    current = program_service.get_current_program(program_repo)
    return _pure.build_review_prompt(
        ReviewPromptSource(
            from_date=from_date,
            to_date=to_date,
            csv=csv,
            rules_body=program_service.get_program_rules(rules_repo).body,
            design_note=None if current is None else current.design_note,
            training_max_records=tuple(exercise_service.list_training_max_records(exercise_repo)),
        ),
        timezone=ZoneInfo(settings.app_timezone),
    )
