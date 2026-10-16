import calendar
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date, timedelta, tzinfo

from features.analytics.types import (
    AnnualVolume,
    Big3Lift,
    Big3Total,
    BodyPartShare,
    BodyPartVolume,
    BucketUnit,
    E1rmPoint,
    ExerciseAnalytics,
    ExerciseVolumeBucket,
    MonthlyCumulativeVolume,
    PeriodSummary,
    TrainingMaxPoint,
    VolumeBucket,
)
from features.exercise.types import BodyPart, CalculationBasis, Exercise, TrainingMax
from features.training_log.types import ExerciseSet, TrainingLog

BIG3_EXERCISE_NAMES = ("スクワット", "ベンチプレス", "デッドリフト")
BIG3_GOAL_KG = 400.0

E1rmCalculator = Callable[[ExerciseSet, CalculationBasis], float]


def summarize_period(logs: Sequence[TrainingLog], *, from_date: date, to_date: date) -> PeriodSummary:
    current = _list_logs_in_period(logs, from_date=from_date, to_date=to_date)
    period = to_date - from_date + timedelta(days=1)
    previous = _list_logs_in_period(logs, from_date=from_date - period, to_date=from_date - timedelta(days=1))
    total_volume = _sum_volume(s for log in current for performed in log.exercises for s in performed.sets)
    previous_volume = _sum_volume(s for log in previous for performed in log.exercises for s in performed.sets)
    training_days = len({log.date for log in current if _has_sets(log)})
    return PeriodSummary(
        total_volume=total_volume,
        change_rate=_calculate_change_rate(total_volume, base=previous_volume),
        training_days=training_days,
        set_count=sum(len(performed.sets) for log in current for performed in log.exercises),
        volume_per_training_day=total_volume / training_days if training_days > 0 else 0.0,
    )


def list_volume_buckets(
    logs: Sequence[TrainingLog],
    *,
    from_date: date,
    to_date: date,
    body_parts: Mapping[int, BodyPart],
    unit: BucketUnit,
) -> list[VolumeBucket]:
    current = _list_logs_in_period(logs, from_date=from_date, to_date=to_date)
    if len(current) == 0:
        return []
    volumes: dict[tuple[date, BodyPart], float] = {}
    for log in current:
        start = _calculate_bucket_start(log.date, unit=unit)
        for performed in log.exercises:
            key = (start, body_parts[performed.exercise_id])
            volumes[key] = volumes.get(key, 0.0) + _sum_volume(performed.sets)
    return [
        VolumeBucket(
            start=start,
            volumes=tuple(
                BodyPartVolume(body_part=body_part, volume=volumes.get((start, body_part), 0.0))
                for body_part in BodyPart
            ),
        )
        for start in _list_bucket_starts(current[0].date, to_date=to_date, unit=unit)
    ]


def list_body_part_shares(
    logs: Sequence[TrainingLog], *, from_date: date, to_date: date, body_parts: Mapping[int, BodyPart]
) -> list[BodyPartShare]:
    volumes = dict.fromkeys(BodyPart, 0.0)
    for log in _list_logs_in_period(logs, from_date=from_date, to_date=to_date):
        for performed in log.exercises:
            volumes[body_parts[performed.exercise_id]] += _sum_volume(performed.sets)
    total_volume = sum(volumes.values())
    ordered = sorted(BodyPart, key=lambda body_part: (-volumes[body_part], list(BodyPart).index(body_part)))
    return [
        BodyPartShare(
            body_part=body_part,
            volume=volumes[body_part],
            share=volumes[body_part] / total_volume if total_volume > 0 else 0.0,
        )
        for body_part in ordered
    ]


def build_annual_volume(logs: Sequence[TrainingLog], *, today: date) -> AnnualVolume:
    last_year = today.year - 1
    last_year_cumulative = _list_monthly_cumulative(logs, year=last_year, until=date(last_year, 12, 31))
    this_year_cumulative = _list_monthly_cumulative(logs, year=today.year, until=today)
    same_day_last_year = today.replace(
        year=last_year, day=min(today.day, calendar.monthrange(last_year, today.month)[1])
    )
    same_day_volume = _sum_volume_between(logs, from_date=date(last_year, 1, 1), to_date=same_day_last_year)
    return AnnualVolume(
        year=today.year,
        this_year=this_year_cumulative,
        last_year=last_year_cumulative,
        change_rate=_calculate_change_rate(this_year_cumulative[-1].cumulative_volume, base=same_day_volume),
        last_year_total_volume=last_year_cumulative[-1].cumulative_volume,
    )


def build_big3_total(
    logs: Sequence[TrainingLog],
    *,
    from_date: date,
    to_date: date,
    exercises: Sequence[Exercise],
    bases: Mapping[int, CalculationBasis],
    calculate_e1rm: E1rmCalculator,
) -> Big3Total:
    current = _list_logs_in_period(logs, from_date=from_date, to_date=to_date)
    exercises_by_name = {exercise.name: exercise for exercise in exercises}
    lifts = []
    for name in BIG3_EXERCISE_NAMES:
        exercise = exercises_by_name.get(name)
        e1rms = (
            []
            if exercise is None
            else [calculate_e1rm(s, bases[exercise.id]) for s in _list_sets(current, exercise_id=exercise.id)]
        )
        lifts.append(Big3Lift(exercise_name=name, e1rm=max(e1rms) if len(e1rms) > 0 else None))
    return Big3Total(
        lifts=tuple(lifts), total=sum(lift.e1rm for lift in lifts if lift.e1rm is not None), goal=BIG3_GOAL_KG
    )


def build_exercise_analytics(
    logs: Sequence[TrainingLog],
    *,
    exercise_id: int,
    basis: CalculationBasis,
    training_maxes: Sequence[TrainingMax],
    from_date: date,
    to_date: date,
    timezone: tzinfo,
    calculate_e1rm: E1rmCalculator,
) -> ExerciseAnalytics:
    performed_logs = [
        log
        for log in _list_logs_in_period(logs, from_date=from_date, to_date=to_date)
        if len(_list_sets([log], exercise_id=exercise_id)) > 0
    ]
    sets = _list_sets(performed_logs, exercise_id=exercise_id)
    e1rm_points = tuple(
        E1rmPoint(
            date=log.date,
            e1rm=max(calculate_e1rm(s, basis) for s in _list_sets([log], exercise_id=exercise_id)),
        )
        for log in performed_logs
    )
    return ExerciseAnalytics(
        exercise_name=basis.name,
        max_weight=max((s.weight for s in sets), default=None),
        max_e1rm=max((point.e1rm for point in e1rm_points), default=None),
        total_volume=_sum_volume(sets),
        e1rm_points=e1rm_points,
        training_max_points=_list_training_max_points(
            training_maxes, owner_id=basis.tm_owner_id, from_date=from_date, to_date=to_date, timezone=timezone
        ),
        weekly_volumes=_list_exercise_volume_buckets(
            performed_logs, exercise_id=exercise_id, to_date=to_date, unit=BucketUnit.week
        ),
        monthly_volumes=_list_exercise_volume_buckets(
            performed_logs, exercise_id=exercise_id, to_date=to_date, unit=BucketUnit.month
        ),
    )


def _list_logs_in_period(logs: Sequence[TrainingLog], *, from_date: date, to_date: date) -> list[TrainingLog]:
    return sorted((log for log in logs if from_date <= log.date <= to_date), key=lambda log: log.date)


def _list_sets(logs: Iterable[TrainingLog], *, exercise_id: int) -> list[ExerciseSet]:
    return [
        s for log in logs for performed in log.exercises if performed.exercise_id == exercise_id for s in performed.sets
    ]


def _has_sets(log: TrainingLog) -> bool:
    return any(len(performed.sets) > 0 for performed in log.exercises)


def _sum_volume(sets: Iterable[ExerciseSet]) -> float:
    return sum((s.weight * s.reps for s in sets), 0.0)


def _sum_volume_between(logs: Sequence[TrainingLog], *, from_date: date, to_date: date) -> float:
    return _sum_volume(
        s
        for log in _list_logs_in_period(logs, from_date=from_date, to_date=to_date)
        for performed in log.exercises
        for s in performed.sets
    )


def _calculate_change_rate(value: float, *, base: float) -> float | None:
    if base == 0:
        return None
    return value / base - 1


def _list_monthly_cumulative(
    logs: Sequence[TrainingLog], *, year: int, until: date
) -> tuple[MonthlyCumulativeVolume, ...]:
    return tuple(
        MonthlyCumulativeVolume(
            month=month,
            cumulative_volume=_sum_volume_between(
                logs,
                from_date=date(year, 1, 1),
                to_date=min(date(year, month, calendar.monthrange(year, month)[1]), until),
            ),
        )
        for month in range(1, until.month + 1)
    )


def _calculate_bucket_start(on: date, *, unit: BucketUnit) -> date:
    match unit:
        case BucketUnit.week:
            return on - timedelta(days=on.weekday())
        case BucketUnit.month:
            return on.replace(day=1)


def _list_bucket_starts(first: date, *, to_date: date, unit: BucketUnit) -> list[date]:
    starts = []
    start = _calculate_bucket_start(first, unit=unit)
    while start <= to_date:
        starts.append(start)
        start = _calculate_next_bucket_start(start, unit=unit)
    return starts


def _calculate_next_bucket_start(start: date, *, unit: BucketUnit) -> date:
    match unit:
        case BucketUnit.week:
            return start + timedelta(days=7)
        case BucketUnit.month:
            return date(start.year + start.month // 12, start.month % 12 + 1, 1)


def _list_exercise_volume_buckets(
    performed_logs: Sequence[TrainingLog], *, exercise_id: int, to_date: date, unit: BucketUnit
) -> tuple[ExerciseVolumeBucket, ...]:
    if len(performed_logs) == 0:
        return ()
    volumes: dict[date, float] = {}
    for log in performed_logs:
        start = _calculate_bucket_start(log.date, unit=unit)
        volumes[start] = volumes.get(start, 0.0) + _sum_volume(_list_sets([log], exercise_id=exercise_id))
    return tuple(
        ExerciseVolumeBucket(start=start, volume=volumes.get(start, 0.0))
        for start in _list_bucket_starts(performed_logs[0].date, to_date=to_date, unit=unit)
    )


def _list_training_max_points(
    training_maxes: Sequence[TrainingMax], *, owner_id: int | None, from_date: date, to_date: date, timezone: tzinfo
) -> tuple[TrainingMaxPoint, ...]:
    if owner_id is None:
        return ()
    history = sorted(
        (tm for tm in training_maxes if tm.exercise_id == owner_id), key=lambda training_max: training_max.effective_at
    )
    dated = [(training_max.effective_at.astimezone(timezone).date(), training_max.value) for training_max in history]
    points = []
    values_at_start = [value for effective_on, value in dated if effective_on <= from_date]
    if len(values_at_start) > 0:
        points.append(TrainingMaxPoint(effective_on=from_date, value=values_at_start[-1]))
    points.extend(
        TrainingMaxPoint(effective_on=effective_on, value=value)
        for effective_on, value in dated
        if from_date < effective_on <= to_date
    )
    return tuple(points)
