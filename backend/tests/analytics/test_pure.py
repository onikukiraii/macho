from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from features.analytics._pure import (
    BIG3_GOAL_KG,
    build_annual_volume,
    build_big3_total,
    build_exercise_analytics,
    list_body_part_shares,
    list_volume_buckets,
    summarize_period,
)
from features.analytics.types import (
    AnnualVolume,
    Big3Lift,
    Big3Total,
    BodyPartShare,
    BucketUnit,
    E1rmPoint,
    ExerciseAnalytics,
    ExerciseVolumeBucket,
    MonthlyCumulativeVolume,
    PeriodSummary,
    TrainingMaxPoint,
)
from features.exercise.types import BodyPart, CalculationBasis, Exercise, TrainingMax, TrainingMaxSource
from features.training_log._pure import calculate_e1rm
from features.training_log.types import ExerciseSet, PerformedExercise, TrainingLog

TOKYO = ZoneInfo("Asia/Tokyo")
BENCH_ID = 1
SQUAT_ID = 2
LAT_ID = 3
PAUSE_BENCH_ID = 4
BODY_PARTS = {BENCH_ID: BodyPart.chest, SQUAT_ID: BodyPart.legs, LAT_ID: BodyPart.back, PAUSE_BENCH_ID: BodyPart.chest}
BENCH_BASIS = CalculationBasis(
    exercise_id=BENCH_ID,
    name="ベンチプレス",
    tm_owner_id=BENCH_ID,
    coefficient=1.0,
    e1rm_divisor=40.0,
    increment_kg=2.5,
    training_max=90.5,
)
SQUAT_BASIS = CalculationBasis(
    exercise_id=SQUAT_ID,
    name="スクワット",
    tm_owner_id=SQUAT_ID,
    coefficient=1.0,
    e1rm_divisor=33.3,
    increment_kg=2.5,
    training_max=120.0,
)
LAT_BASIS = CalculationBasis(
    exercise_id=LAT_ID,
    name="ラットプルダウン",
    tm_owner_id=None,
    coefficient=1.0,
    e1rm_divisor=33.3,
    increment_kg=2.5,
    training_max=None,
)
PAUSE_BENCH_BASIS = CalculationBasis(
    exercise_id=PAUSE_BENCH_ID,
    name="ポーズベンチ",
    tm_owner_id=BENCH_ID,
    coefficient=0.9,
    e1rm_divisor=40.0,
    increment_kg=2.5,
    training_max=90.5,
)
BASES = {BENCH_ID: BENCH_BASIS, SQUAT_ID: SQUAT_BASIS, LAT_ID: LAT_BASIS, PAUSE_BENCH_ID: PAUSE_BENCH_BASIS}


def _exercise(id: int, name: str) -> Exercise:
    return Exercise(
        id=id,
        uid=f"exercise-{id}",
        name=name,
        body_part=BODY_PARTS[id],
        parent_id=None,
        coefficient=None,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        default_rest_seconds=180,
    )


EXERCISES = [
    _exercise(BENCH_ID, "ベンチプレス"),
    _exercise(SQUAT_ID, "スクワット"),
    _exercise(LAT_ID, "ラットプルダウン"),
]


def _set(weight: float, reps: int, *, rir: int | None = None, order: int = 1) -> ExerciseSet:
    return ExerciseSet(order=order, weight=weight, reps=reps, rir=rir)


def _performed(exercise_id: int, *sets: ExerciseSet) -> PerformedExercise:
    return PerformedExercise(
        id=exercise_id,
        uid=f"performed-{exercise_id}",
        exercise_id=exercise_id,
        planned_exercise_id=None,
        order=exercise_id,
        memo="",
        sets=sets,
    )


def _log(on: date, *exercises: PerformedExercise) -> TrainingLog:
    return TrainingLog(id=on.toordinal(), uid=f"log-{on}", date=on, program_day_id=None, memo="", exercises=exercises)


def _calculate_e1rm(exercise_set: ExerciseSet, basis: CalculationBasis) -> float:
    return calculate_e1rm(exercise_set, basis=basis)


PERIOD_LOGS = [
    _log(date(2026, 9, 20), _performed(SQUAT_ID, _set(100, 5), _set(100, 5, order=2), _set(100, 5, order=3))),
    _log(
        date(2026, 10, 1), _performed(BENCH_ID, _set(80, 5), _set(80, 5, order=2)), _performed(SQUAT_ID, _set(100, 5))
    ),
    _log(date(2026, 10, 3), _performed(LAT_ID, _set(50, 10))),
    _log(date(2026, 10, 15), _performed(BENCH_ID, _set(80, 5))),
]


class TestSummarizePeriod:
    def test_期間内の全種目の総ボリュームとトレーニング日数と総セット数と1回あたりのボリュームを出す(self) -> None:
        summary = summarize_period(PERIOD_LOGS, from_date=date(2026, 10, 1), to_date=date(2026, 10, 14))

        assert (
            summary.total_volume,
            summary.training_days,
            summary.set_count,
            summary.volume_per_training_day,
        ) == (1800.0, 2, 4, 900.0)

    def test_前の同じ長さの期間に対する増減率を出す(self) -> None:
        summary = summarize_period(PERIOD_LOGS, from_date=date(2026, 10, 1), to_date=date(2026, 10, 14))

        assert summary.change_rate == pytest.approx(0.2)

    def test_期間に記録が無ければ0で前の期間にも無ければ増減率は無い(self) -> None:
        summary = summarize_period(PERIOD_LOGS, from_date=date(2026, 11, 1), to_date=date(2026, 11, 14))

        assert summary == PeriodSummary(
            total_volume=0.0, change_rate=None, training_days=0, set_count=0, volume_per_training_day=0.0
        )


BUCKET_LOGS = [
    _log(date(2026, 9, 29), _performed(BENCH_ID, _set(80, 10)), _performed(SQUAT_ID, _set(100, 5))),
    _log(date(2026, 10, 6), _performed(LAT_ID, _set(50, 10))),
    _log(date(2026, 10, 14), _performed(BENCH_ID, _set(80, 5))),
]


class TestListVolumeBuckets:
    @pytest.mark.parametrize(
        ("unit", "expected"),
        [
            (
                BucketUnit.week,
                [
                    (date(2026, 9, 28), {BodyPart.chest: 800.0, BodyPart.legs: 500.0}),
                    (date(2026, 10, 5), {BodyPart.back: 500.0}),
                    (date(2026, 10, 12), {BodyPart.chest: 400.0}),
                ],
            ),
            (
                BucketUnit.month,
                [
                    (date(2026, 9, 1), {BodyPart.chest: 800.0, BodyPart.legs: 500.0}),
                    (date(2026, 10, 1), {BodyPart.chest: 400.0, BodyPart.back: 500.0}),
                ],
            ),
        ],
    )
    def test_週は月曜始まりで月は1日始まりで部位ごとに集計する(
        self, unit: BucketUnit, expected: list[tuple[date, dict[BodyPart, float]]]
    ) -> None:
        buckets = list_volume_buckets(
            BUCKET_LOGS, from_date=date(2026, 9, 28), to_date=date(2026, 10, 14), body_parts=BODY_PARTS, unit=unit
        )

        assert [
            (bucket.start, {v.body_part: v.volume for v in bucket.volumes if v.volume > 0}) for bucket in buckets
        ] == expected


class TestListBodyPartShares:
    def test_部位ごとの量と割合を多い順に並べる(self) -> None:
        shares = list_body_part_shares(
            BUCKET_LOGS + [_log(date(2026, 10, 10), _performed(BENCH_ID, _set(0, 10)))],
            from_date=date(2026, 9, 28),
            to_date=date(2026, 10, 14),
            body_parts=BODY_PARTS,
        )

        assert shares == [
            BodyPartShare(body_part=BodyPart.chest, volume=1200.0, share=1200 / 2200),
            BodyPartShare(body_part=BodyPart.back, volume=500.0, share=500 / 2200),
            BodyPartShare(body_part=BodyPart.legs, volume=500.0, share=500 / 2200),
            BodyPartShare(body_part=BodyPart.shoulders, volume=0.0, share=0.0),
            BodyPartShare(body_part=BodyPart.arms, volume=0.0, share=0.0),
            BodyPartShare(body_part=BodyPart.abs, volume=0.0, share=0.0),
        ]


class TestBuildAnnualVolume:
    def test_今年は今日まで前の年は12月までの月ごとの累計と同じ日までの増減率と前の年の合計を出す(self) -> None:
        logs = [
            _log(date(2025, 1, 10), _performed(LAT_ID, _set(100, 10))),
            _log(date(2025, 10, 14), _performed(LAT_ID, _set(60, 10))),
            _log(date(2025, 10, 15), _performed(LAT_ID, _set(70, 10))),
            _log(date(2025, 12, 31), _performed(LAT_ID, _set(30, 10))),
            _log(date(2026, 1, 5), _performed(LAT_ID, _set(120, 10))),
            _log(date(2026, 3, 1), _performed(LAT_ID, _set(60, 10))),
            _log(date(2026, 10, 14), _performed(LAT_ID, _set(40, 10))),
        ]

        annual = build_annual_volume(logs, today=date(2026, 10, 14))

        this_year = [1200.0, 1200.0, 1800.0, 1800.0, 1800.0, 1800.0, 1800.0, 1800.0, 1800.0, 2200.0]
        last_year = [1000.0] * 9 + [2300.0, 2300.0, 2600.0]
        assert annual == AnnualVolume(
            year=2026,
            this_year=tuple(
                MonthlyCumulativeVolume(month=m, cumulative_volume=v) for m, v in enumerate(this_year, start=1)
            ),
            last_year=tuple(
                MonthlyCumulativeVolume(month=m, cumulative_volume=v) for m, v in enumerate(last_year, start=1)
            ),
            change_rate=0.375,
            last_year_total_volume=2600.0,
        )


class TestBuildBig3Total:
    def test_期間内のBIG3の推定1RMの最大値を合計し目標を添える(self) -> None:
        logs = [
            _log(date(2026, 9, 1), _performed(BENCH_ID, _set(100, 5))),
            _log(date(2026, 10, 1), _performed(BENCH_ID, _set(80, 5, rir=1), _set(85, 1, order=2))),
            _log(date(2026, 10, 2), _performed(SQUAT_ID, _set(100, 5))),
        ]

        big3 = build_big3_total(
            logs,
            from_date=date(2026, 9, 28),
            to_date=date(2026, 10, 14),
            exercises=EXERCISES,
            bases=BASES,
            calculate_e1rm=_calculate_e1rm,
        )

        assert big3 == Big3Total(
            lifts=(
                Big3Lift(exercise_name="スクワット", e1rm=115.0),
                Big3Lift(exercise_name="ベンチプレス", e1rm=92.0),
                Big3Lift(exercise_name="デッドリフト", e1rm=None),
            ),
            total=207.0,
            goal=BIG3_GOAL_KG,
        )


EXERCISE_LOGS = [
    _log(date(2026, 9, 24), _performed(BENCH_ID, _set(100, 1))),
    _log(date(2026, 10, 1), _performed(BENCH_ID, _set(80, 5, rir=1), _set(70, 8, order=2))),
    _log(date(2026, 10, 8), _performed(BENCH_ID, _set(82.5, 3, rir=2)), _performed(PAUSE_BENCH_ID, _set(72, 5, rir=1))),
]
TRAINING_MAXES = [
    TrainingMax(
        exercise_id=BENCH_ID,
        value=85.5,
        effective_at=datetime(2026, 9, 6, 15, 0, tzinfo=UTC),
        source=TrainingMaxSource.manual,
        reason="初期値",
    ),
    TrainingMax(
        exercise_id=BENCH_ID,
        value=88.0,
        effective_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        source=TrainingMaxSource.auto,
        reason="評価",
    ),
    TrainingMax(
        exercise_id=BENCH_ID,
        value=90.5,
        effective_at=datetime(2026, 10, 11, 15, 0, tzinfo=UTC),
        source=TrainingMaxSource.auto,
        reason="評価",
    ),
    TrainingMax(
        exercise_id=SQUAT_ID,
        value=120.0,
        effective_at=datetime(2026, 10, 4, 15, 0, tzinfo=UTC),
        source=TrainingMaxSource.auto,
        reason="評価",
    ),
]


def _analytics(exercise_id: int, basis: CalculationBasis) -> ExerciseAnalytics:
    return build_exercise_analytics(
        EXERCISE_LOGS,
        exercise_id=exercise_id,
        basis=basis,
        training_maxes=TRAINING_MAXES,
        from_date=date(2026, 10, 1),
        to_date=date(2026, 10, 14),
        timezone=TOKYO,
        calculate_e1rm=_calculate_e1rm,
    )


class TestBuildExerciseAnalytics:
    def test_期間内の最大重量と推定1RMの最大値と総ボリュームを出す(self) -> None:
        analytics = _analytics(BENCH_ID, BENCH_BASIS)

        assert (analytics.max_weight, analytics.max_e1rm, analytics.total_volume) == (82.5, 92.8, 1207.5)

    def test_推定1RMは記録ごとのトップセットでトレーニングマックスは期間の開始時点の値から並べる(self) -> None:
        analytics = _analytics(BENCH_ID, BENCH_BASIS)

        assert (analytics.e1rm_points, analytics.training_max_points) == (
            (E1rmPoint(date=date(2026, 10, 1), e1rm=92.0), E1rmPoint(date=date(2026, 10, 8), e1rm=92.8)),
            (
                TrainingMaxPoint(effective_on=date(2026, 10, 1), value=88.0),
                TrainingMaxPoint(effective_on=date(2026, 10, 12), value=90.5),
            ),
        )

    def test_派生種目は換算係数で割った推定1RMと親のトレーニングマックスを並べる(self) -> None:
        analytics = _analytics(PAUSE_BENCH_ID, PAUSE_BENCH_BASIS)

        assert (analytics.e1rm_points, analytics.training_max_points) == (
            (E1rmPoint(date=date(2026, 10, 8), e1rm=92.0),),
            (
                TrainingMaxPoint(effective_on=date(2026, 10, 1), value=88.0),
                TrainingMaxPoint(effective_on=date(2026, 10, 12), value=90.5),
            ),
        )

    def test_その種目だけの週ごとと月ごとの総ボリュームを出す(self) -> None:
        analytics = _analytics(BENCH_ID, BENCH_BASIS)

        assert (analytics.weekly_volumes, analytics.monthly_volumes) == (
            (
                ExerciseVolumeBucket(start=date(2026, 9, 28), volume=960.0),
                ExerciseVolumeBucket(start=date(2026, 10, 5), volume=247.5),
                ExerciseVolumeBucket(start=date(2026, 10, 12), volume=0.0),
            ),
            (ExerciseVolumeBucket(start=date(2026, 10, 1), volume=1207.5),),
        )
