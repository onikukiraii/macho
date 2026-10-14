from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from common.errors import BusinessRuleViolation
from features.exercise._pure import classify_exercise, select_training_max, validate_derivation
from features.exercise.types import BodyPart, Exercise, ExerciseKind, TrainingMax, TrainingMaxSource

TOKYO = ZoneInfo("Asia/Tokyo")


def _exercise(*, id: int, name: str, parent_id: int | None = None) -> Exercise:
    return Exercise(
        id=id,
        uid=f"uid-{id}",
        name=name,
        body_part=BodyPart.chest,
        parent_id=parent_id,
        coefficient=None if parent_id is None else 0.87,
        e1rm_divisor=40.0 if parent_id is None else None,
        increment_kg=2.5,
        default_rest_seconds=180,
    )


def _training_max(*, value: float, effective_at: datetime) -> TrainingMax:
    return TrainingMax(
        exercise_id=1, value=value, effective_at=effective_at, source=TrainingMaxSource.manual, reason="入力"
    )


BENCH = _exercise(id=1, name="ベンチプレス")
PAUSE_BENCH = _exercise(id=2, name="ポーズベンチ", parent_id=1)
SHOULDER_PRESS = _exercise(id=3, name="ショルダープレス")


class TestClassifyExercise:
    def test_TM_の履歴と派生元の有無で3種類に分かれる(self) -> None:
        kinds = [
            classify_exercise(BENCH, has_training_max=True),
            classify_exercise(PAUSE_BENCH, has_training_max=False),
            classify_exercise(SHOULDER_PRESS, has_training_max=False),
        ]

        assert kinds == [ExerciseKind.training_max, ExerciseKind.derived, ExerciseKind.double_progression]


class TestValidateDerivation:
    @pytest.mark.parametrize(
        ("exercise_id", "parent", "has_derived_exercises", "coefficient", "e1rm_divisor", "message"),
        [
            pytest.param(3, PAUSE_BENCH, False, 0.9, None, "派生種目は派生元に選択できません", id="派生種目を派生元"),
            pytest.param(1, BENCH, False, 0.9, None, "種目自身は派生元に選択できません", id="自分を派生元"),
            pytest.param(
                3, BENCH, True, 0.9, None, "派生種目を持つ種目は派生種目にできません", id="派生種目を持つ種目"
            ),
            pytest.param(3, BENCH, False, None, None, "派生種目には換算係数を入力してください", id="換算係数が空"),
            pytest.param(
                3, None, False, None, None, "派生元が無い種目には分母を入力してください", id="派生元なしで分母が空"
            ),
        ],
    )
    def test_派生元と換算係数と分母の組み合わせが不正なら保存できない(
        self,
        exercise_id: int,
        parent: Exercise | None,
        has_derived_exercises: bool,
        coefficient: float | None,
        e1rm_divisor: float | None,
        message: str,
    ) -> None:
        with pytest.raises(BusinessRuleViolation, match=f"^{message}$"):
            validate_derivation(
                exercise_id=exercise_id,
                parent=parent,
                has_derived_exercises=has_derived_exercises,
                has_training_max=False,
                coefficient=coefficient,
                e1rm_divisor=e1rm_divisor,
            )

    def test_TM_の履歴がある種目は派生種目にできない(self) -> None:
        with pytest.raises(BusinessRuleViolation, match="^トレーニングマックスの履歴がある種目は派生種目にできません$"):
            validate_derivation(
                exercise_id=SHOULDER_PRESS.id,
                parent=BENCH,
                has_derived_exercises=False,
                has_training_max=True,
                coefficient=0.6,
                e1rm_divisor=None,
            )


class TestSelectTrainingMax:
    @pytest.mark.parametrize(
        ("registered_at", "on", "expected"),
        [
            pytest.param(datetime(2026, 10, 14, 0, 0, tzinfo=TOKYO), date(2026, 10, 14), 90.5, id="00:00_当日"),
            pytest.param(datetime(2026, 10, 14, 8, 0, tzinfo=TOKYO), date(2026, 10, 14), 90.5, id="08:00_当日"),
            pytest.param(datetime(2026, 10, 14, 8, 59, tzinfo=TOKYO), date(2026, 10, 14), 90.5, id="08:59_当日"),
            pytest.param(datetime(2026, 10, 14, 9, 0, tzinfo=TOKYO), date(2026, 10, 14), 90.5, id="09:00_当日"),
            pytest.param(datetime(2026, 10, 14, 23, 30, tzinfo=TOKYO), date(2026, 10, 14), 90.5, id="23:30_当日"),
            pytest.param(datetime(2026, 10, 14, 0, 0, tzinfo=TOKYO), date(2026, 10, 13), 88.0, id="00:00_前日"),
            pytest.param(datetime(2026, 10, 14, 8, 0, tzinfo=TOKYO), date(2026, 10, 13), 88.0, id="08:00_前日"),
            pytest.param(datetime(2026, 10, 14, 8, 59, tzinfo=TOKYO), date(2026, 10, 13), 88.0, id="08:59_前日"),
            pytest.param(datetime(2026, 10, 14, 9, 0, tzinfo=TOKYO), date(2026, 10, 13), 88.0, id="09:00_前日"),
            pytest.param(datetime(2026, 10, 14, 23, 30, tzinfo=TOKYO), date(2026, 10, 13), 88.0, id="23:30_前日"),
        ],
    )
    def test_日本時間で登録した日の記録から使われる(self, registered_at: datetime, on: date, expected: float) -> None:
        newest_first = [
            _training_max(value=90.5, effective_at=registered_at.astimezone(UTC)),
            _training_max(value=88.0, effective_at=datetime(2026, 10, 1, 0, 0, tzinfo=UTC)),
        ]

        assert select_training_max(newest_first, on=on, timezone=TOKYO) == expected
