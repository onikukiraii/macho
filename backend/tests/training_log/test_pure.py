from datetime import date

import pytest

from features.exercise.types import CalculationBasis
from features.program.types import PlannedExercise, ProgramDay, ProgramWeek, Weekday
from features.training_log._pure import (
    build_export_csv,
    calculate_e1rm,
    calculate_target_weight,
    calculate_week_start,
    evaluate_week,
    list_day_options,
    list_day_statuses,
    select_top_set,
)
from features.training_log.types import DayStatus, ExerciseSet, PerformedExercise, ScheduledDay, TrainingLog

BENCH_ID = 1
PAUSE_BENCH_ID = 2
LAT_PULLDOWN_ID = 3


def _bench(*, training_max: float | None = 88.0) -> CalculationBasis:
    return CalculationBasis(
        exercise_id=BENCH_ID,
        name="ベンチプレス",
        tm_owner_id=BENCH_ID,
        coefficient=1.0,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        training_max=training_max,
    )


def _pause_bench(*, training_max: float | None = 88.0) -> CalculationBasis:
    return CalculationBasis(
        exercise_id=PAUSE_BENCH_ID,
        name="ポーズベンチ",
        tm_owner_id=BENCH_ID,
        coefficient=0.87,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        training_max=training_max,
    )


LAT_PULLDOWN = CalculationBasis(
    exercise_id=LAT_PULLDOWN_ID,
    name="ラットプルダウン",
    tm_owner_id=None,
    coefficient=1.0,
    e1rm_divisor=33.3,
    increment_kg=2.5,
    training_max=None,
)


def _planned(
    *,
    exercise_id: int,
    reps: int = 5,
    reps_max: int | None = None,
    target_rpe: float | None = None,
    target_percent: float | None = None,
) -> PlannedExercise:
    return PlannedExercise(
        id=100 + exercise_id,
        exercise_id=exercise_id,
        order=1,
        sets=3,
        reps=reps,
        reps_max=reps_max,
        target_rpe=target_rpe,
        target_percent=target_percent,
    )


def _set(order: int, weight: float, reps: int, rir: int | None = None) -> ExerciseSet:
    return ExerciseSet(order=order, weight=weight, reps=reps, rir=rir)


def _performed(
    *, id: int, exercise_id: int, sets: tuple[ExerciseSet, ...], planned_id: int | None
) -> PerformedExercise:
    return PerformedExercise(
        id=id,
        uid=f"pe-{id}",
        exercise_id=exercise_id,
        planned_exercise_id=planned_id,
        order=1,
        memo="",
        sets=sets,
    )


def _log(
    *, id: int, on: date, exercises: tuple[PerformedExercise, ...], program_day_id: int | None = None
) -> TrainingLog:
    return TrainingLog(id=id, uid=f"log-{id}", date=on, program_day_id=program_day_id, memo="", exercises=exercises)


def _schedule(days_per_week: list[int]) -> list[ScheduledDay]:
    schedule = []
    for week_index, day_count in enumerate(days_per_week, start=1):
        week = ProgramWeek(week=week_index, label=f"ブロック{week_index}", days=())
        for day_number in range(1, day_count + 1):
            day = ProgramDay(
                id=week_index * 10 + day_number,
                uid=f"day-{week_index}-{day_number}",
                day=day_number,
                weekday=Weekday.mon,
                planned_exercises=(),
            )
            schedule.append(ScheduledDay(week=week, day=day, guide_date=date(2026, 9, 28)))
    return schedule


class TestCalculateE1rm:
    @pytest.mark.parametrize(
        ("exercise_set", "basis", "expected"),
        [
            pytest.param(_set(1, 77.5, 5, 2), _bench(), 91.1, id="ベンチプレス"),
            pytest.param(_set(1, 70.0, 5, 2), _pause_bench(), 94.5, id="派生種目は派生元へ換算する"),
        ],
    )
    def test_重量と回数と_RIR_から推定1RM_を求める(
        self, exercise_set: ExerciseSet, basis: CalculationBasis, expected: float
    ) -> None:
        assert calculate_e1rm(exercise_set, basis=basis) == expected

    def test_RIR_が空なら_0_として計算する(self) -> None:
        assert calculate_e1rm(_set(1, 80.0, 5, None), basis=_bench()) == 90.0


class TestSelectTopSet:
    def test_推定1RM_が同じなら番号の小さいセットを選ぶ(self) -> None:
        sets = [_set(2, 72.0, 10, 0), _set(1, 80.0, 5, 0)]

        top_set = select_top_set(sets, e1rm_divisor=40.0)

        assert top_set == _set(1, 80.0, 5, 0)


class TestCalculateTargetWeight:
    @pytest.mark.parametrize(
        ("basis", "planned", "expected"),
        [
            pytest.param(_bench(), _planned(exercise_id=BENCH_ID, target_rpe=7.5), 75.0, id="RPE"),
            pytest.param(_bench(), _planned(exercise_id=BENCH_ID, target_percent=70.0), 62.5, id="パーセント"),
            pytest.param(
                _pause_bench(), _planned(exercise_id=PAUSE_BENCH_ID, target_rpe=7.0), 65.0, id="派生種目の換算係数"
            ),
            pytest.param(
                _bench(training_max=147.5),
                _planned(exercise_id=BENCH_ID, target_percent=50.0),
                75.0,
                id="ちょうど半分は切り上げる",
            ),
            pytest.param(
                _bench(training_max=147.0),
                _planned(exercise_id=BENCH_ID, target_percent=50.0),
                72.5,
                id="半分に届かなければ切り下げる",
            ),
        ],
    )
    def test_TM_と予定の強度から目標重量を求める(
        self, basis: CalculationBasis, planned: PlannedExercise, expected: float
    ) -> None:
        assert calculate_target_weight(basis=basis, planned=planned, previous_sets=()) == expected

    @pytest.mark.parametrize(
        ("previous_reps", "expected"),
        [
            pytest.param((12, 12, 12), 57.5, id="全セットが上限に届いた"),
            pytest.param((12, 12, 11), 55.0, id="1セットが上限に届かない"),
        ],
    )
    def test_ダブルプログレッションは前回の全セットが上限に届けば上げる幅を足す(
        self, previous_reps: tuple[int, int, int], expected: float
    ) -> None:
        planned = _planned(exercise_id=LAT_PULLDOWN_ID, reps=10, reps_max=12)
        previous_sets = tuple(_set(order, 55.0, reps) for order, reps in enumerate(previous_reps, start=1))

        assert calculate_target_weight(basis=LAT_PULLDOWN, planned=planned, previous_sets=previous_sets) == expected

    @pytest.mark.parametrize(
        ("planned", "previous_sets"),
        [
            pytest.param(_planned(exercise_id=LAT_PULLDOWN_ID, reps=10, reps_max=12), (), id="前回の記録が無い"),
            pytest.param(
                _planned(exercise_id=LAT_PULLDOWN_ID, reps=10),
                (_set(1, 55.0, 10),),
                id="予定に回数の上限が無い",
            ),
        ],
    )
    def test_ダブルプログレッションの目標重量を出さない(
        self, planned: PlannedExercise, previous_sets: tuple[ExerciseSet, ...]
    ) -> None:
        assert calculate_target_weight(basis=LAT_PULLDOWN, planned=planned, previous_sets=previous_sets) is None


class TestEvaluateWeek:
    @pytest.mark.parametrize(
        ("training_max", "weight", "expected_after"),
        [
            pytest.param(87.5, 80.0, [90.0], id="ちょうど_TM_+2.5"),
            pytest.param(87.6, 80.0, [], id="0.1_足りない"),
            pytest.param(87.5, 100.0, [90.0], id="大きく超えても_2.5kg_まで"),
        ],
    )
    def test_週の最大の推定1RM_が_TM_より_2_5_以上大きければ_2_5kg_だけ上げる(
        self, training_max: float, weight: float, expected_after: list[float]
    ) -> None:
        log = _log(
            id=1,
            on=date(2026, 10, 6),
            exercises=(_performed(id=1, exercise_id=BENCH_ID, sets=(_set(1, weight, 5, 0),), planned_id=None),),
        )

        updates = evaluate_week([log], bases={BENCH_ID: _bench(training_max=training_max)})

        assert [update.after for update in updates] == expected_after

    @pytest.mark.parametrize(
        "log",
        [
            pytest.param(
                _log(
                    id=1,
                    on=date(2026, 10, 6),
                    program_day_id=11,
                    exercises=(
                        _performed(id=1, exercise_id=PAUSE_BENCH_ID, sets=(_set(1, 70.0, 5, 2),), planned_id=102),
                    ),
                ),
                id="派生種目のセット",
            ),
            pytest.param(
                _log(
                    id=1,
                    on=date(2026, 10, 6),
                    exercises=(_performed(id=1, exercise_id=BENCH_ID, sets=(_set(1, 80.0, 5, 2),), planned_id=None),),
                ),
                id="予定外の記録のセット",
            ),
        ],
    )
    def test_派生種目と予定外の記録のセットも派生元の判定に加わる(self, log: TrainingLog) -> None:
        bases = {BENCH_ID: _bench(training_max=88.0), PAUSE_BENCH_ID: _pause_bench(training_max=88.0)}

        updates = evaluate_week([log], bases=bases)

        assert [(update.exercise_id, update.before, update.after) for update in updates] == [(BENCH_ID, 88.0, 90.5)]


class TestCalculateWeekStart:
    @pytest.mark.parametrize(
        ("on", "expected"),
        [
            pytest.param(date(2026, 10, 4), date(2026, 9, 28), id="日曜は前の月曜の週"),
            pytest.param(date(2026, 10, 5), date(2026, 10, 5), id="月曜から新しい週"),
        ],
    )
    def test_月曜始まりで週を分ける(self, on: date, expected: date) -> None:
        assert calculate_week_start(on) == expected


class TestListDayOptions:
    @pytest.mark.parametrize(
        ("last_recorded_dates", "expected"),
        [
            pytest.param({}, [("day-1-1", True), ("day-1-2", False)], id="記録が無い"),
            pytest.param(
                {11: date(2026, 9, 28), 12: date(2026, 9, 29), 21: date(2026, 10, 5), 22: date(2026, 10, 6)},
                [("day-2-2", False)],
                id="最後の_Day_まで記録済み",
            ),
        ],
    )
    def test_記録が無ければ最初の_Day_が次で最後まで記録済みなら次は無い(
        self, last_recorded_dates: dict[int, date], expected: list[tuple[str, bool]]
    ) -> None:
        options = list_day_options(_schedule([2, 2]), last_recorded_dates=last_recorded_dates)

        assert [(option.scheduled_day.day.uid, option.is_next) for option in options] == expected


class TestListDayStatuses:
    def test_最後に記録した_Day_の次が次になり前は消化済みで後は未消化(self) -> None:
        recorded_day_ids = {11, 12, 13, 14, 21, 22, 23, 24}

        statuses = list_day_statuses(_schedule([4, 4, 4]), recorded_day_ids=recorded_day_ids)

        assert statuses == {
            11: DayStatus.done,
            12: DayStatus.done,
            13: DayStatus.done,
            14: DayStatus.done,
            21: DayStatus.done,
            22: DayStatus.done,
            23: DayStatus.done,
            24: DayStatus.done,
            31: DayStatus.next,
            32: DayStatus.pending,
            33: DayStatus.pending,
            34: DayStatus.pending,
        }

    def test_記録した_Day_の間で記録の無い_Day_は未実施になる(self) -> None:
        statuses = list_day_statuses(_schedule([3]), recorded_day_ids={11, 13})

        assert statuses == {11: DayStatus.done, 12: DayStatus.missed, 13: DayStatus.done}


class TestBuildExportCsv:
    def test_セットごとに10列の行を出し目標重量は記録の日付の_TM_で計算する(self) -> None:
        planned = _planned(exercise_id=BENCH_ID, target_rpe=8.0)
        scheduled_days = {
            24: ScheduledDay(
                week=ProgramWeek(week=2, label="ブロックA", days=()),
                day=ProgramDay(id=24, uid="day-2-4", day=4, weekday=Weekday.fri, planned_exercises=(planned,)),
                guide_date=date(2026, 10, 9),
            ),
            31: ScheduledDay(
                week=ProgramWeek(week=3, label="ブロックA", days=()),
                day=ProgramDay(id=31, uid="day-3-1", day=1, weekday=Weekday.mon, planned_exercises=(planned,)),
                guide_date=date(2026, 10, 12),
            ),
        }
        logs = [
            _log(
                id=1,
                on=date(2026, 10, 9),
                program_day_id=24,
                exercises=(
                    _performed(
                        id=1,
                        exercise_id=BENCH_ID,
                        sets=(_set(1, 75.0, 5, 2), _set(2, 75.0, 5, None)),
                        planned_id=planned.id,
                    ),
                ),
            ),
            _log(
                id=2,
                on=date(2026, 10, 13),
                program_day_id=31,
                exercises=(_performed(id=2, exercise_id=BENCH_ID, sets=(_set(1, 77.5, 5, 2),), planned_id=planned.id),),
            ),
        ]
        bases_by_date = {
            date(2026, 10, 9): {BENCH_ID: _bench(training_max=88.0)},
            date(2026, 10, 13): {BENCH_ID: _bench(training_max=90.5)},
        }

        csv_text = build_export_csv(
            logs, from_date=date(2026, 10, 1), bases_by_date=bases_by_date, scheduled_days=scheduled_days
        )

        assert csv_text.splitlines() == [
            "日付,Day,種目,重量,回数,RIR,e1RM,予定のレップ,目標RPE,目標重量",
            "2026-10-09,第2週 Day4,ベンチプレス,75,5,2,88.1,5,8,75",
            "2026-10-09,第2週 Day4,ベンチプレス,75,5,,84.4,5,8,75",
            "2026-10-13,第3週 Day1,ベンチプレス,77.5,5,2,91.1,5,8,77.5",
        ]
