from datetime import date, timedelta
from zoneinfo import ZoneInfo

from common.config import settings
from common.errors import BusinessRuleViolation
from features.analytics import _pure
from features.analytics.types import BucketUnit, ExerciseAnalytics, Overview
from features.exercise import service as exercise_service
from features.exercise.protocol import ExerciseRepository
from features.exercise.types import CalculationBasis
from features.training_log import service as training_log_service
from features.training_log.protocol import TrainingLogRepository
from features.training_log.types import ExerciseSet


def get_overview(
    *,
    training_log_repo: TrainingLogRepository,
    exercise_repo: ExerciseRepository,
    from_date: date,
    to_date: date,
    today: date,
) -> Overview:
    if from_date > to_date:
        raise BusinessRuleViolation("開始日は終了日以前の日付にしてください")
    period = to_date - from_date + timedelta(days=1)
    logs = training_log_service.list_training_logs_between(
        training_log_repo,
        from_date=min(from_date - period, date(today.year - 1, 1, 1)),
        to_date=max(to_date, today),
    )
    exercises = [resolved.exercise for resolved in exercise_service.list_exercises(exercise_repo)]
    body_parts = {exercise.id: exercise.body_part for exercise in exercises}
    return Overview(
        summary=_pure.summarize_period(logs, from_date=from_date, to_date=to_date),
        weekly_volumes=tuple(
            _pure.list_volume_buckets(
                logs, from_date=from_date, to_date=to_date, body_parts=body_parts, unit=BucketUnit.week
            )
        ),
        monthly_volumes=tuple(
            _pure.list_volume_buckets(
                logs, from_date=from_date, to_date=to_date, body_parts=body_parts, unit=BucketUnit.month
            )
        ),
        body_part_shares=tuple(
            _pure.list_body_part_shares(logs, from_date=from_date, to_date=to_date, body_parts=body_parts)
        ),
        annual=_pure.build_annual_volume(logs, today=today),
        big3=_pure.build_big3_total(
            logs,
            from_date=from_date,
            to_date=to_date,
            exercises=exercises,
            bases=exercise_service.get_calculation_bases(exercise_repo, on=to_date),
            calculate_e1rm=_calculate_e1rm,
        ),
    )


def get_exercise_analytics(
    *,
    training_log_repo: TrainingLogRepository,
    exercise_repo: ExerciseRepository,
    exercise_uid: str,
    from_date: date,
    to_date: date,
) -> ExerciseAnalytics:
    exercise = exercise_service.get_exercise(exercise_repo, uid=exercise_uid).exercise.exercise
    logs = training_log_service.list_training_logs_between(training_log_repo, from_date=from_date, to_date=to_date)
    return _pure.build_exercise_analytics(
        logs,
        exercise_id=exercise.id,
        basis=exercise_service.get_calculation_bases(exercise_repo, on=to_date)[exercise.id],
        training_maxes=[record.training_max for record in exercise_service.list_training_max_records(exercise_repo)],
        from_date=from_date,
        to_date=to_date,
        timezone=ZoneInfo(settings.app_timezone),
        calculate_e1rm=_calculate_e1rm,
    )


def _calculate_e1rm(exercise_set: ExerciseSet, basis: CalculationBasis) -> float:
    return training_log_service.calculate_e1rm(exercise_set, basis=basis)
