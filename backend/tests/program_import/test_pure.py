from dataclasses import replace
from datetime import date

import pytest

from features.exercise.types import BodyPart, CalculationBasis, Exercise
from features.program.types import Weekday
from features.program_import._pure import (
    BOTH_TARGETS_MESSAGE,
    DERIVED_PARENT_MESSAGE,
    DUPLICATE_DAY_MESSAGE,
    DUPLICATE_NEW_EXERCISE_MESSAGE,
    DUPLICATE_WEEK_MESSAGE,
    EXISTING_EXERCISE_NAME_MESSAGE,
    MISSING_COEFFICIENT_MESSAGE,
    MISSING_DIVISOR_MESSAGE,
    MISSING_TARGET_MESSAGE,
    REPS_MAX_BELOW_REPS_MESSAGE,
    START_DATE_AFTER_TODAY_MESSAGE,
    START_DATE_NOT_AFTER_CURRENT_MESSAGE,
    START_DATE_NOT_AFTER_LAST_RECORD_MESSAGE,
    UNEXPECTED_REPS_MAX_MESSAGE,
    UNEXPECTED_TARGET_MESSAGE,
    UNKNOWN_EXERCISE_MESSAGE,
    UNKNOWN_PARENT_MESSAGE,
    build_preview,
    build_preview_bases,
    validate_draft,
)
from features.program_import.types import (
    DraftDay,
    DraftExercise,
    DraftIssue,
    DraftPlannedExercise,
    DraftWeek,
    ProgramDraft,
)
from features.training_log._pure import calculate_training_max_weight

BENCH = Exercise(
    id=1,
    uid="bench",
    name="ベンチプレス",
    body_part=BodyPart.chest,
    parent_id=None,
    coefficient=None,
    e1rm_divisor=40.0,
    increment_kg=2.5,
    default_rest_seconds=180,
)
LAT_PULLDOWN = Exercise(
    id=2,
    uid="lat",
    name="ラットプルダウン",
    body_part=BodyPart.back,
    parent_id=None,
    coefficient=None,
    e1rm_divisor=33.3,
    increment_kg=2.5,
    default_rest_seconds=90,
)
PAUSE_BENCH = Exercise(
    id=3,
    uid="pause",
    name="ポーズベンチ",
    body_part=BodyPart.chest,
    parent_id=1,
    coefficient=0.9,
    e1rm_divisor=None,
    increment_kg=2.5,
    default_rest_seconds=180,
)
EXERCISES = [BENCH, LAT_PULLDOWN, PAUSE_BENCH]
BASES = {
    1: CalculationBasis(
        exercise_id=1,
        name="ベンチプレス",
        tm_owner_id=1,
        coefficient=1.0,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        training_max=90.5,
    ),
    2: CalculationBasis(
        exercise_id=2,
        name="ラットプルダウン",
        tm_owner_id=None,
        coefficient=1.0,
        e1rm_divisor=33.3,
        increment_kg=2.5,
        training_max=None,
    ),
    3: CalculationBasis(
        exercise_id=3,
        name="ポーズベンチ",
        tm_owner_id=1,
        coefficient=0.9,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        training_max=90.5,
    ),
}
LARSEN_BENCH = DraftExercise(
    name="ラーセンベンチ",
    body_part=BodyPart.chest,
    parent_name="ベンチプレス",
    coefficient=0.85,
    e1rm_divisor=None,
    increment_kg=2.5,
    default_rest_seconds=180,
)


def _planned(
    name: str,
    *,
    reps: int = 5,
    reps_max: int | None = None,
    target_rpe: float | None = None,
    target_percent: float | None = None,
) -> DraftPlannedExercise:
    return DraftPlannedExercise(
        exercise_name=name,
        sets=3,
        reps=reps,
        reps_max=reps_max,
        target_rpe=target_rpe,
        target_percent=target_percent,
    )


def _week(week: int, *days: DraftDay) -> DraftWeek:
    return DraftWeek(week=week, label="導入", days=days)


def _day(day: int, *exercises: DraftPlannedExercise) -> DraftDay:
    return DraftDay(day=day, weekday=Weekday.mon, exercises=exercises)


def _draft(
    *weeks: DraftWeek, new_exercises: tuple[DraftExercise, ...] = (), start_date: date = date(2026, 10, 19)
) -> ProgramDraft:
    return ProgramDraft(
        name="ベンチ スモロフ Jr",
        start_date=start_date,
        tm_auto_update=False,
        design_note="",
        new_exercises=new_exercises,
        weeks=weeks,
    )


VALID_BENCH = _planned("ベンチプレス", target_percent=70)
TODAY = date(2026, 10, 19)


class TestValidateDraft:
    @pytest.mark.parametrize(
        ("draft", "current_start_date", "expected"),
        [
            (
                _draft(_week(1, _day(1, _planned("デッドリフト", target_rpe=8)))),
                None,
                [DraftIssue(location="第1週 Day 1「デッドリフト」", message=UNKNOWN_EXERCISE_MESSAGE)],
            ),
            (
                _draft(_week(2, _day(3, _planned("ポーズベンチ", target_rpe=8, target_percent=70)))),
                None,
                [DraftIssue(location="第2週 Day 3「ポーズベンチ」", message=BOTH_TARGETS_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, _planned("ベンチプレス")))),
                None,
                [DraftIssue(location="第1週 Day 1「ベンチプレス」", message=MISSING_TARGET_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, _planned("ラットプルダウン", reps=8, reps_max=12, target_rpe=8)))),
                None,
                [DraftIssue(location="第1週 Day 1「ラットプルダウン」", message=UNEXPECTED_TARGET_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, _planned("ベンチプレス", reps_max=8, target_rpe=8)))),
                None,
                [DraftIssue(location="第1週 Day 1「ベンチプレス」", message=UNEXPECTED_REPS_MAX_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, VALID_BENCH)), _week(1, _day(1, VALID_BENCH))),
                None,
                [DraftIssue(location="第1週", message=DUPLICATE_WEEK_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(2, VALID_BENCH), _day(2, VALID_BENCH))),
                None,
                [DraftIssue(location="第1週 Day 2", message=DUPLICATE_DAY_MESSAGE)],
            ),
            (
                _draft(
                    _week(1, _day(1, VALID_BENCH)),
                    new_exercises=(replace(LARSEN_BENCH, name="ポーズベンチ"),),
                ),
                None,
                [DraftIssue(location="new_exercises「ポーズベンチ」", message=EXISTING_EXERCISE_NAME_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, VALID_BENCH)), new_exercises=(LARSEN_BENCH, LARSEN_BENCH)),
                None,
                [DraftIssue(location="new_exercises「ラーセンベンチ」", message=DUPLICATE_NEW_EXERCISE_MESSAGE)],
            ),
            (
                _draft(
                    _week(1, _day(1, VALID_BENCH)),
                    new_exercises=(replace(LARSEN_BENCH, parent_name="スクワット"),),
                ),
                None,
                [DraftIssue(location="new_exercises「ラーセンベンチ」", message=UNKNOWN_PARENT_MESSAGE)],
            ),
            (
                _draft(
                    _week(1, _day(1, VALID_BENCH)),
                    new_exercises=(replace(LARSEN_BENCH, parent_name="ポーズベンチ"),),
                ),
                None,
                [DraftIssue(location="new_exercises「ラーセンベンチ」", message=DERIVED_PARENT_MESSAGE)],
            ),
            (
                _draft(
                    _week(1, _day(1, VALID_BENCH)),
                    new_exercises=(replace(LARSEN_BENCH, parent_name=None, coefficient=None),),
                ),
                None,
                [DraftIssue(location="new_exercises「ラーセンベンチ」", message=MISSING_DIVISOR_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, VALID_BENCH)), new_exercises=(replace(LARSEN_BENCH, coefficient=None),)),
                None,
                [DraftIssue(location="new_exercises「ラーセンベンチ」", message=MISSING_COEFFICIENT_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, _planned("ラットプルダウン", reps=12, reps_max=8)))),
                None,
                [DraftIssue(location="第1週 Day 1「ラットプルダウン」", message=REPS_MAX_BELOW_REPS_MESSAGE)],
            ),
            (
                _draft(_week(1, _day(1, VALID_BENCH)), start_date=date(2026, 9, 28)),
                date(2026, 9, 28),
                [DraftIssue(location="start_date", message=START_DATE_NOT_AFTER_CURRENT_MESSAGE)],
            ),
        ],
    )
    def test_規則に反する箇所を場所と理由つきで返す(
        self, draft: ProgramDraft, current_start_date: date | None, expected: list[DraftIssue]
    ) -> None:
        assert (
            validate_draft(
                draft,
                exercises=EXERCISES,
                bases=BASES,
                current_start_date=current_start_date,
                last_recorded_on=None,
                today=TODAY,
            )
            == expected
        )

    @pytest.mark.parametrize(
        ("start_date", "last_recorded_on", "expected"),
        [
            (date(2026, 10, 20), None, [DraftIssue(location="start_date", message=START_DATE_AFTER_TODAY_MESSAGE)]),
            (
                date(2026, 10, 14),
                date(2026, 10, 14),
                [DraftIssue(location="start_date", message=START_DATE_NOT_AFTER_LAST_RECORD_MESSAGE)],
            ),
            (date(2026, 10, 19), date(2026, 10, 18), []),
        ],
    )
    def test_開始日は最後の記録日より後で今日以前に限る(
        self, start_date: date, last_recorded_on: date | None, expected: list[DraftIssue]
    ) -> None:
        draft = _draft(_week(1, _day(1, VALID_BENCH)), start_date=start_date)

        assert (
            validate_draft(
                draft,
                exercises=EXERCISES,
                bases=BASES,
                current_start_date=None,
                last_recorded_on=last_recorded_on,
                today=TODAY,
            )
            == expected
        )

    def test_規則に反する箇所が複数あればすべて返す(self) -> None:
        draft = _draft(
            _week(1, _day(1, _planned("デッドリフト", target_rpe=8)), _day(2, _planned("ベンチプレス"))),
            new_exercises=(replace(LARSEN_BENCH, coefficient=None),),
        )

        assert validate_draft(
            draft, exercises=EXERCISES, bases=BASES, current_start_date=None, last_recorded_on=None, today=TODAY
        ) == [
            DraftIssue(location="new_exercises「ラーセンベンチ」", message=MISSING_COEFFICIENT_MESSAGE),
            DraftIssue(location="第1週 Day 1「デッドリフト」", message=UNKNOWN_EXERCISE_MESSAGE),
            DraftIssue(location="第1週 Day 2「ベンチプレス」", message=MISSING_TARGET_MESSAGE),
        ]

    def test_規則を満たせば空(self) -> None:
        draft = _draft(
            _week(1, _day(1, VALID_BENCH, _planned("ラーセンベンチ", reps=8, target_rpe=7))),
            new_exercises=(LARSEN_BENCH,),
            start_date=date(2026, 10, 19),
        )

        assert (
            validate_draft(
                draft,
                exercises=EXERCISES,
                bases=BASES,
                current_start_date=date(2026, 9, 28),
                last_recorded_on=date(2026, 10, 18),
                today=TODAY,
            )
            == []
        )


def _calculate_weight(basis: CalculationBasis, planned: DraftPlannedExercise) -> float | None:
    return calculate_training_max_weight(
        basis, reps=planned.reps, target_rpe=planned.target_rpe, target_percent=planned.target_percent
    )


def _preview_weight(planned: DraftPlannedExercise, *, new_exercises: tuple[DraftExercise, ...] = ()) -> float | None:
    draft = _draft(_week(1, _day(1, planned)), new_exercises=new_exercises)
    preview = build_preview(
        draft,
        preview_bases=build_preview_bases(draft, exercises=EXERCISES, bases=BASES),
        calculate_weight=_calculate_weight,
    )
    return preview.weeks[0].days[0].exercises[0].target_weight


class TestBuildPreview:
    @pytest.mark.parametrize(
        ("planned", "expected"),
        [
            (_planned("ベンチプレス", reps=6, target_percent=70), 62.5),
            (_planned("ベンチプレス", reps=5, target_rpe=8), 77.5),
            (_planned("ポーズベンチ", reps=5, target_percent=80), 65.0),
        ],
    )
    def test_トレーニングマックスを使う種目は目標重量を出す(
        self, planned: DraftPlannedExercise, expected: float
    ) -> None:
        assert _preview_weight(planned) == expected

    @pytest.mark.parametrize(
        "planned",
        [_planned("ラットプルダウン", reps=8, reps_max=12), _planned("ラットプルダウン", reps=10)],
    )
    def test_トレーニングマックスを使わない種目は目標重量を出さない(self, planned: DraftPlannedExercise) -> None:
        assert _preview_weight(planned) is None
