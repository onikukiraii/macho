import csv
import io
from collections.abc import Collection, Mapping, Sequence
from datetime import date, datetime, time, timedelta, tzinfo
from decimal import ROUND_HALF_UP, Decimal

from common.errors import BusinessRuleViolation
from features.exercise.types import BodyPart, CalculationBasis, TrainingMaxUpdate
from features.program.types import PlannedExercise
from features.training_log.types import (
    DayOption,
    DayStatus,
    ExerciseSet,
    PreviousPerformance,
    PreviousResult,
    ScheduledDay,
    TopSet,
    TrainingLog,
)

TRAINING_MAX_STEP_KG = 2.5
PLATE_STEP_KG = 2.5
EXPORT_HEADER = ["日付", "Day", "種目", "重量", "回数", "RIR", "e1RM", "予定のレップ", "目標RPE", "目標重量"]


def validate_training_log_date(on: date, *, today: date) -> None:
    if on > today:
        raise BusinessRuleViolation("未来の日付ではトレーニング記録を作成できません")


def validate_period(*, from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise BusinessRuleViolation("開始日は終了日以前の日付にしてください")


def calculate_next_exercise_order(log: TrainingLog) -> int:
    return max((performed.order for performed in log.exercises), default=0) + 1


def calculate_week_start(on: date) -> date:
    return on - timedelta(days=on.weekday())


def calculate_week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def calculate_next_week_start_at(week_start: date, *, timezone: tzinfo) -> datetime:
    return datetime.combine(week_start + timedelta(days=7), time(), tzinfo=timezone)


def find_week_to_evaluate(*, latest_recorded_on: date, new_date: date) -> date | None:
    latest_week_start = calculate_week_start(latest_recorded_on)
    if calculate_week_start(new_date) <= latest_week_start:
        return None
    return latest_week_start


def calculate_e1rm(exercise_set: ExerciseSet, *, basis: CalculationBasis) -> float:
    return _round_half_up(
        _estimate_raw_e1rm(exercise_set, e1rm_divisor=basis.e1rm_divisor) / basis.coefficient, step=0.1
    )


def select_top_set(sets: Sequence[ExerciseSet], *, e1rm_divisor: float) -> ExerciseSet | None:
    if len(sets) == 0:
        return None
    return max(sets, key=lambda s: (_estimate_raw_e1rm(s, e1rm_divisor=e1rm_divisor), -s.order))


def build_previous_result(previous: PreviousPerformance | None, *, e1rm_divisor: float) -> PreviousResult | None:
    if previous is None:
        return None
    top_set = select_top_set(previous.sets, e1rm_divisor=e1rm_divisor)
    if top_set is None:
        return None
    return PreviousResult(date=previous.date, top_set=top_set, sets=previous.sets)


def list_top_sets(log: TrainingLog, *, bases: Mapping[int, CalculationBasis]) -> tuple[TopSet, ...]:
    top_sets = []
    for performed in log.exercises:
        basis = bases[performed.exercise_id]
        top_set = select_top_set(performed.sets, e1rm_divisor=basis.e1rm_divisor)
        if top_set is not None:
            top_sets.append(TopSet(exercise_name=basis.name, exercise_set=top_set))
    return tuple(top_sets)


def list_trained_body_parts(log: TrainingLog, *, body_parts: Mapping[int, BodyPart]) -> tuple[BodyPart, ...]:
    trained = {body_parts[performed.exercise_id] for performed in log.exercises if len(performed.sets) > 0}
    return tuple(body_part for body_part in BodyPart if body_part in trained)


def calculate_target_weight(
    *, basis: CalculationBasis, planned: PlannedExercise | None, previous_sets: Sequence[ExerciseSet]
) -> float | None:
    if planned is None:
        return None
    if basis.tm_owner_id is not None:
        return _calculate_training_max_weight(basis, planned)
    is_substituted = planned.exercise_id != basis.exercise_id
    if is_substituted or planned.reps_max is None:
        return None
    top_set = select_top_set(previous_sets, e1rm_divisor=basis.e1rm_divisor)
    if top_set is None:
        return None
    reps_max = planned.reps_max
    if all(s.reps >= reps_max for s in previous_sets):
        return top_set.weight + basis.increment_kg
    return top_set.weight


def evaluate_week(logs: Sequence[TrainingLog], *, bases: Mapping[int, CalculationBasis]) -> list[TrainingMaxUpdate]:
    best_sets: dict[int, tuple[float, str, ExerciseSet]] = {}
    for log in logs:
        for performed in log.exercises:
            basis = bases[performed.exercise_id]
            if basis.tm_owner_id is None:
                continue
            for exercise_set in performed.sets:
                e1rm = calculate_e1rm(exercise_set, basis=basis)
                best = best_sets.get(basis.tm_owner_id)
                if best is None or e1rm > best[0]:
                    best_sets[basis.tm_owner_id] = (e1rm, basis.name, exercise_set)

    updates = []
    for owner_id, basis in bases.items():
        best = best_sets.get(owner_id)
        if best is None or basis.training_max is None:
            continue
        e1rm, set_exercise_name, exercise_set = best
        threshold = basis.training_max + TRAINING_MAX_STEP_KG
        if e1rm < threshold:
            continue
        updates.append(
            TrainingMaxUpdate(
                exercise_id=owner_id,
                exercise_name=basis.name,
                before=basis.training_max,
                after=threshold,
                reason=(
                    f"{set_exercise_name} {exercise_set.weight:g}kg×{exercise_set.reps}回 "
                    f"RIR{_rir_or_zero(exercise_set)} → e1RM {e1rm:g} ≧ {threshold:g}"
                ),
            )
        )
    return updates


def find_next_day(schedule: Sequence[ScheduledDay], *, recorded_day_ids: Collection[int]) -> ScheduledDay | None:
    last_index = _find_last_recorded_index(schedule, recorded_day_ids=recorded_day_ids)
    next_index = 0 if last_index is None else last_index + 1
    if next_index >= len(schedule):
        return None
    return schedule[next_index]


def list_day_options(schedule: Sequence[ScheduledDay], *, last_recorded_dates: Mapping[int, date]) -> list[DayOption]:
    recorded_day_ids = last_recorded_dates.keys()
    next_day = find_next_day(schedule, recorded_day_ids=recorded_day_ids)
    candidates = [] if next_day is None else [s for s in schedule if s.week.week == next_day.week.week]
    last_index = _find_last_recorded_index(schedule, recorded_day_ids=recorded_day_ids)
    if last_index is not None and schedule[last_index] not in candidates:
        candidates.append(schedule[last_index])
    return [
        DayOption(
            scheduled_day=candidate,
            is_next=candidate == next_day,
            last_recorded_on=last_recorded_dates.get(candidate.day.id),
        )
        for candidate in candidates
    ]


def list_day_statuses(schedule: Sequence[ScheduledDay], *, recorded_day_ids: Collection[int]) -> dict[int, DayStatus]:
    next_day = find_next_day(schedule, recorded_day_ids=recorded_day_ids)
    next_index = len(schedule) if next_day is None else schedule.index(next_day)
    statuses = {}
    for index, scheduled_day in enumerate(schedule):
        if index == next_index:
            status = DayStatus.next
        elif scheduled_day.day.id in recorded_day_ids:
            status = DayStatus.done
        elif index < next_index:
            status = DayStatus.missed
        else:
            status = DayStatus.pending
        statuses[scheduled_day.day.id] = status
    return statuses


def format_day_label(scheduled_day: ScheduledDay) -> str:
    return f"第{scheduled_day.week.week}週 Day{scheduled_day.day.day}"


def find_planned_exercise(
    scheduled_day: ScheduledDay | None, planned_exercise_id: int | None
) -> PlannedExercise | None:
    if scheduled_day is None or planned_exercise_id is None:
        return None
    return next(
        (planned for planned in scheduled_day.day.planned_exercises if planned.id == planned_exercise_id),
        None,
    )


def list_export_dates(logs: Sequence[TrainingLog], *, from_date: date) -> list[date]:
    return sorted({log.date for log in logs if log.date >= from_date})


def build_export_csv(
    logs: Sequence[TrainingLog],
    *,
    from_date: date,
    bases_by_date: Mapping[date, Mapping[int, CalculationBasis]],
    scheduled_days: Mapping[int, ScheduledDay],
) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_HEADER)
    previous_sets_by_exercise: dict[int, tuple[ExerciseSet, ...]] = {}
    for log in logs:
        if log.date >= from_date:
            rows = _build_export_rows(
                log,
                bases=bases_by_date[log.date],
                scheduled_day=None if log.program_day_id is None else scheduled_days.get(log.program_day_id),
                previous_sets_by_exercise=previous_sets_by_exercise,
            )
            writer.writerows(rows)
        for performed in log.exercises:
            if len(performed.sets) > 0:
                previous_sets_by_exercise[performed.exercise_id] = performed.sets
    return buffer.getvalue()


def _build_export_rows(
    log: TrainingLog,
    *,
    bases: Mapping[int, CalculationBasis],
    scheduled_day: ScheduledDay | None,
    previous_sets_by_exercise: Mapping[int, tuple[ExerciseSet, ...]],
) -> list[list[str]]:
    rows = []
    day_label = "" if scheduled_day is None else format_day_label(scheduled_day)
    for performed in log.exercises:
        basis = bases[performed.exercise_id]
        planned = find_planned_exercise(scheduled_day, performed.planned_exercise_id)
        target_weight = calculate_target_weight(
            basis=basis, planned=planned, previous_sets=previous_sets_by_exercise.get(performed.exercise_id, ())
        )
        for exercise_set in performed.sets:
            rows.append(
                [
                    log.date.isoformat(),
                    day_label,
                    basis.name,
                    f"{exercise_set.weight:g}",
                    str(exercise_set.reps),
                    _format_optional(exercise_set.rir),
                    f"{calculate_e1rm(exercise_set, basis=basis):g}",
                    "" if planned is None else _format_planned_reps(planned),
                    _format_optional(None if planned is None else planned.target_rpe),
                    _format_optional(target_weight),
                ]
            )
    return rows


def _calculate_training_max_weight(basis: CalculationBasis, planned: PlannedExercise) -> float | None:
    if basis.training_max is None:
        return None
    base_weight = basis.training_max * basis.coefficient
    if planned.target_percent is not None:
        return _round_half_up(base_weight * planned.target_percent / 100, step=PLATE_STEP_KG)
    if planned.target_rpe is not None:
        reps_in_reserve = 10 - planned.target_rpe
        return _round_half_up(
            base_weight / (1 + (planned.reps + reps_in_reserve) / basis.e1rm_divisor), step=PLATE_STEP_KG
        )
    return None


def _find_last_recorded_index(schedule: Sequence[ScheduledDay], *, recorded_day_ids: Collection[int]) -> int | None:
    recorded_indexes = [index for index, s in enumerate(schedule) if s.day.id in recorded_day_ids]
    if len(recorded_indexes) == 0:
        return None
    return recorded_indexes[-1]


def _estimate_raw_e1rm(exercise_set: ExerciseSet, *, e1rm_divisor: float) -> float:
    return exercise_set.weight * (1 + (exercise_set.reps + _rir_or_zero(exercise_set)) / e1rm_divisor)


def _rir_or_zero(exercise_set: ExerciseSet) -> int:
    return 0 if exercise_set.rir is None else exercise_set.rir


def _round_half_up(value: float, *, step: float) -> float:
    # 浮動小数の誤差で 73.75 が 73.7499... になると切り下がるため、桁を落としてから丸める
    steps = Decimal(repr(round(value / step, 9))).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return float(steps * Decimal(repr(step)))


def _format_planned_reps(planned: PlannedExercise) -> str:
    if planned.reps_max is None:
        return str(planned.reps)
    return f"{planned.reps}-{planned.reps_max}"


def _format_optional(value: float | None) -> str:
    return "" if value is None else f"{value:g}"
