from collections.abc import Iterable, Sequence
from datetime import date
from uuid import uuid4
from zoneinfo import ZoneInfo

from common.config import settings
from common.errors import Conflict, NotFound
from features.exercise import service as exercise_service
from features.exercise.protocol import ExerciseRepository
from features.exercise.types import CalculationBasis, TrainingMaxUpdate
from features.program import service as program_service
from features.program.protocol import ProgramRepository
from features.program.types import Program
from features.training_log import _pure
from features.training_log._pure import (
    build_export_csv,
    build_previous_result,
    calculate_next_exercise_order,
    calculate_next_week_start_at,
    calculate_target_weight,
    calculate_week_end,
    calculate_week_start,
    evaluate_week,
    find_planned_exercise,
    find_week_to_evaluate,
    format_day_label,
    list_day_options,
    list_day_statuses,
    list_export_dates,
    list_top_sets,
    list_trained_body_parts,
    validate_period,
    validate_training_log_date,
)
from features.training_log.protocol import TrainingLogRepository
from features.training_log.types import (
    DayOption,
    ExerciseHistoryRecord,
    ExerciseSet,
    NewPerformedExercise,
    PerformedExerciseDetail,
    ProgramProgress,
    ScheduledDay,
    TrainingLog,
    TrainingLogCreated,
    TrainingLogDetail,
    TrainingLogSummary,
)


def list_training_logs(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    from_date: date,
    to_date: date,
) -> list[TrainingLogSummary]:
    validate_period(from_date=from_date, to_date=to_date)
    return _summarize(
        repo.list_between(from_date=from_date, to_date=to_date),
        exercise_repo=exercise_repo,
        program_repo=program_repo,
        on=to_date,
    )


def get_latest_training_log(
    repo: TrainingLogRepository, *, exercise_repo: ExerciseRepository, program_repo: ProgramRepository
) -> TrainingLogSummary | None:
    latest = repo.get_latest()
    if latest is None:
        return None
    return _summarize([latest], exercise_repo=exercise_repo, program_repo=program_repo, on=latest.date)[0]


def get_latest_recorded_date(repo: TrainingLogRepository) -> date | None:
    latest = repo.get_latest()
    return None if latest is None else latest.date


def get_day_options(repo: TrainingLogRepository, *, program_repo: ProgramRepository) -> list[DayOption]:
    program = program_service.get_current_program(program_repo)
    if program is None:
        return []
    schedule = _schedule(program)
    last_recorded_dates = repo.list_last_recorded_dates([scheduled_day.day.id for scheduled_day in schedule])
    return list_day_options(schedule, last_recorded_dates=last_recorded_dates)


def get_program_progress(repo: TrainingLogRepository, *, program_repo: ProgramRepository) -> ProgramProgress | None:
    program = program_service.get_current_program(program_repo)
    if program is None:
        return None
    schedule = _schedule(program)
    last_recorded_dates = repo.list_last_recorded_dates([scheduled_day.day.id for scheduled_day in schedule])
    return ProgramProgress(
        program=program, day_statuses=list_day_statuses(schedule, recorded_day_ids=last_recorded_dates.keys())
    )


def create_training_log(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    on: date,
    program_day_uid: str | None,
    today: date,
) -> TrainingLogCreated:
    validate_training_log_date(on, today=today)
    scheduled_day = None if program_day_uid is None else _find_scheduled_day(program_repo, uid=program_day_uid, on=on)
    # 記録の作成より先に評価を commit する。記録の作成が失敗しても TM の更新を取りこぼさない
    updates = _evaluate_previous_week(repo, exercise_repo=exercise_repo, program_repo=program_repo, on=on)
    planned_exercises = () if scheduled_day is None else scheduled_day.day.planned_exercises
    training_log = repo.create(
        uid=str(uuid4()),
        date=on,
        program_day_id=None if scheduled_day is None else scheduled_day.day.id,
        exercises=[
            NewPerformedExercise(
                uid=str(uuid4()), exercise_id=planned.exercise_id, planned_exercise_id=planned.id, order=planned.order
            )
            for planned in planned_exercises
        ],
    )
    return TrainingLogCreated(training_log=training_log, training_max_updates=updates)


def get_training_log(
    repo: TrainingLogRepository, *, exercise_repo: ExerciseRepository, program_repo: ProgramRepository, uid: str
) -> TrainingLogDetail:
    return _build_detail(repo.get(uid), repo=repo, exercise_repo=exercise_repo, program_repo=program_repo)


def update_training_log_memo(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    uid: str,
    memo: str,
) -> TrainingLogDetail:
    training_log = repo.update_memo(uid, memo=memo)
    return _build_detail(training_log, repo=repo, exercise_repo=exercise_repo, program_repo=program_repo)


def delete_training_log(repo: TrainingLogRepository, *, uid: str) -> None:
    repo.delete(uid)


def add_performed_exercise(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    uid: str,
    exercise_uid: str,
) -> TrainingLogDetail:
    training_log = repo.get(uid)
    exercise = exercise_service.get_exercise(exercise_repo, uid=exercise_uid).exercise.exercise
    updated = repo.add_exercise(
        uid,
        exercise=NewPerformedExercise(
            uid=str(uuid4()),
            exercise_id=exercise.id,
            planned_exercise_id=None,
            order=calculate_next_exercise_order(training_log),
        ),
    )
    return _build_detail(updated, repo=repo, exercise_repo=exercise_repo, program_repo=program_repo)


def replace_performed_exercise(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    performed_uid: str,
    exercise_uid: str,
) -> TrainingLogDetail:
    exercise = exercise_service.get_exercise(exercise_repo, uid=exercise_uid).exercise.exercise
    training_log = repo.replace_performed_exercise(performed_uid, exercise_id=exercise.id)
    return _build_detail(training_log, repo=repo, exercise_repo=exercise_repo, program_repo=program_repo)


def update_performed_exercise_memo(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    performed_uid: str,
    memo: str,
) -> TrainingLogDetail:
    training_log = repo.update_performed_exercise_memo(performed_uid, memo=memo)
    return _build_detail(training_log, repo=repo, exercise_repo=exercise_repo, program_repo=program_repo)


def replace_sets(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    performed_uid: str,
    sets: Sequence[ExerciseSet],
) -> PerformedExerciseDetail:
    training_log = repo.replace_sets(performed_uid, sets=sets)
    detail = _build_detail(training_log, repo=repo, exercise_repo=exercise_repo, program_repo=program_repo)
    return next(performed for performed in detail.exercises if performed.performed.uid == performed_uid)


def list_exercise_history(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    exercise_uid: str,
) -> list[ExerciseHistoryRecord]:
    exercise = exercise_service.get_exercise(exercise_repo, uid=exercise_uid).exercise.exercise
    entries = repo.list_exercise_history(exercise.id)
    scheduled_days = _index_scheduled_days(program_repo, [entry.date for entry in entries])
    return [
        ExerciseHistoryRecord(entry=entry, scheduled_day=_lookup(scheduled_days, entry.program_day_id))
        for entry in entries
    ]


def export_training_logs(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    from_date: date,
    to_date: date,
) -> str:
    validate_period(from_date=from_date, to_date=to_date)
    # 期間より前の記録も読むのは、期間の最初の記録の前回実績からダブルプログレッションの目標重量を出すため
    training_logs = repo.list_on_or_before(to_date)
    exported_dates = list_export_dates(training_logs, from_date=from_date)
    return build_export_csv(
        training_logs,
        from_date=from_date,
        bases_by_date={on: exercise_service.get_calculation_bases(exercise_repo, on=on) for on in exported_dates},
        scheduled_days=_index_scheduled_days(program_repo, exported_dates),
    )


def list_training_logs_between(repo: TrainingLogRepository, *, from_date: date, to_date: date) -> list[TrainingLog]:
    validate_period(from_date=from_date, to_date=to_date)
    return repo.list_between(from_date=from_date, to_date=to_date)


def calculate_e1rm(exercise_set: ExerciseSet, *, basis: CalculationBasis) -> float:
    return _pure.calculate_e1rm(exercise_set, basis=basis)


def calculate_training_max_weight(
    basis: CalculationBasis, *, reps: int, target_rpe: float | None, target_percent: float | None
) -> float | None:
    return _pure.calculate_training_max_weight(basis, reps=reps, target_rpe=target_rpe, target_percent=target_percent)


def count_export_sets(repo: TrainingLogRepository, *, from_date: date, to_date: date) -> int:
    validate_period(from_date=from_date, to_date=to_date)
    return repo.count_sets_between(from_date=from_date, to_date=to_date)


def _evaluate_previous_week(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    on: date,
) -> tuple[TrainingMaxUpdate, ...]:
    latest = repo.get_latest()
    if latest is None:
        return ()
    week_start = find_week_to_evaluate(latest_recorded_on=latest.date, new_date=on)
    if week_start is None:
        return ()
    if exercise_service.is_week_evaluated(exercise_repo, week_start=week_start):
        return ()
    program = program_service.get_program_in_progress_on(program_repo, on=latest.date)
    if program is None or not program.tm_auto_update:
        return ()
    week_end = calculate_week_end(week_start)
    updates = evaluate_week(
        repo.list_between(from_date=week_start, to_date=week_end),
        bases=exercise_service.get_calculation_bases(exercise_repo, on=week_end),
    )
    try:
        exercise_service.record_weekly_evaluation(
            exercise_repo,
            week_start=week_start,
            effective_at=calculate_next_week_start_at(week_start, timezone=ZoneInfo(settings.app_timezone)),
            updates=updates,
        )
    except Conflict:
        # 並行した記録の作成が同じ週を先に評価した。TM はそちらで更新済みなので、評価済みとして記録の作成へ進む
        return ()
    return tuple(updates)


def mark_week_evaluated(exercise_repo: ExerciseRepository, *, on: date) -> None:
    week_start = calculate_week_start(on)
    exercise_service.record_weekly_evaluation(
        exercise_repo,
        week_start=week_start,
        effective_at=calculate_next_week_start_at(week_start, timezone=ZoneInfo(settings.app_timezone)),
        updates=[],
    )


def format_scheduled_day_label(scheduled_day: ScheduledDay | None) -> str | None:
    return None if scheduled_day is None else format_day_label(scheduled_day)


def _summarize(
    training_logs: Sequence[TrainingLog],
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    on: date,
) -> list[TrainingLogSummary]:
    bases = exercise_service.get_calculation_bases(exercise_repo, on=on)
    body_parts = {
        resolved.exercise.id: resolved.exercise.body_part for resolved in exercise_service.list_exercises(exercise_repo)
    }
    scheduled_days = _index_scheduled_days(program_repo, [training_log.date for training_log in training_logs])
    return [
        TrainingLogSummary(
            training_log=training_log,
            scheduled_day=_lookup(scheduled_days, training_log.program_day_id),
            top_sets=list_top_sets(training_log, bases=bases),
            body_parts=list_trained_body_parts(training_log, body_parts=body_parts),
        )
        for training_log in training_logs
    ]


def _build_detail(
    training_log: TrainingLog,
    *,
    repo: TrainingLogRepository,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
) -> TrainingLogDetail:
    scheduled_day = _lookup(_index_scheduled_days(program_repo, [training_log.date]), training_log.program_day_id)
    bases = exercise_service.get_calculation_bases(exercise_repo, on=training_log.date)
    exercises = {resolved.exercise.id: resolved.exercise for resolved in exercise_service.list_exercises(exercise_repo)}
    details = []
    for performed in training_log.exercises:
        basis = bases[performed.exercise_id]
        previous = repo.find_previous_performance(exercise_id=performed.exercise_id, before=training_log)
        planned = find_planned_exercise(scheduled_day, performed.planned_exercise_id)
        details.append(
            PerformedExerciseDetail(
                performed=performed,
                exercise=exercises[performed.exercise_id],
                planned=planned,
                target_weight=calculate_target_weight(
                    basis=basis, planned=planned, previous_sets=() if previous is None else previous.sets
                ),
                previous=build_previous_result(previous, e1rm_divisor=basis.e1rm_divisor),
            )
        )
    return TrainingLogDetail(training_log=training_log, scheduled_day=scheduled_day, exercises=tuple(details))


def _find_scheduled_day(program_repo: ProgramRepository, *, uid: str, on: date) -> ScheduledDay:
    program = program_service.get_program_in_progress_on(program_repo, on=on)
    schedule = [] if program is None else _schedule(program)
    scheduled_day = next((candidate for candidate in schedule if candidate.day.uid == uid), None)
    if scheduled_day is None:
        raise NotFound(f"Day が見つかりません: uid={uid}")
    return scheduled_day


def _index_scheduled_days(program_repo: ProgramRepository, dates: Iterable[date]) -> dict[int, ScheduledDay]:
    # 取得したプログラムの開始日より前の日付だけを次の取得に回す。取得の回数は期間にまたがるプログラムの数で済む
    scheduled_days: dict[int, ScheduledDay] = {}
    remaining = sorted(set(dates), reverse=True)
    while len(remaining) > 0:
        program = program_service.get_program_in_progress_on(program_repo, on=remaining[0])
        if program is None:
            break
        scheduled_days.update({scheduled_day.day.id: scheduled_day for scheduled_day in _schedule(program)})
        remaining = [on for on in remaining if on < program.start_date]
    return scheduled_days


def _lookup(scheduled_days: dict[int, ScheduledDay], program_day_id: int | None) -> ScheduledDay | None:
    if program_day_id is None:
        return None
    return scheduled_days.get(program_day_id)


def _schedule(program: Program) -> list[ScheduledDay]:
    return [
        ScheduledDay(
            week=day_in_week.week,
            day=day_in_week.day,
            guide_date=program_service.calculate_guide_date(
                program.start_date, week=day_in_week.week.week, weekday=day_in_week.day.weekday
            ),
        )
        for day_in_week in program_service.list_days_in_order(program)
    ]
