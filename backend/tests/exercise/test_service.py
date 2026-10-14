import pytest
from sqlalchemy.orm import Session

from common.errors import BusinessRuleViolation, Conflict
from features.exercise.repository import DbExerciseRepository
from features.exercise.service import add_training_max, create_exercise, update_exercise
from features.exercise.types import BodyPart, ResolvedExercise


def _create(
    repo: DbExerciseRepository,
    name: str,
    *,
    parent_uid: str | None = None,
    coefficient: float | None = None,
) -> ResolvedExercise:
    return create_exercise(
        repo,
        name=name,
        body_part=BodyPart.chest,
        parent_uid=parent_uid,
        coefficient=coefficient,
        e1rm_divisor=None if parent_uid is not None else 40.0,
        increment_kg=2.5,
        default_rest_seconds=180,
    )


def _update(repo: DbExerciseRepository, uid: str, name: str, *, parent_uid: str | None) -> ResolvedExercise:
    return update_exercise(
        repo,
        uid=uid,
        name=name,
        body_part=BodyPart.chest,
        parent_uid=parent_uid,
        coefficient=0.87 if parent_uid is not None else None,
        e1rm_divisor=None if parent_uid is not None else 40.0,
        increment_kg=2.5,
        default_rest_seconds=180,
    )


class TestAddTrainingMax:
    def test_派生種目には_TM_を登録できず履歴も書かれない(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        bench = _create(repo, "ベンチプレス")
        pause_bench = _create(repo, "ポーズベンチ", parent_uid=bench.exercise.uid, coefficient=0.87)

        with pytest.raises(BusinessRuleViolation, match="^派生種目にはトレーニングマックスを登録できません$"):
            add_training_max(repo, uid=pause_bench.exercise.uid, value=80.0, reason="入力")

        assert repo.list_training_maxes() == []


class TestUpdateExercise:
    def test_TM_の履歴が無い派生種目を持たない種目に派生元を設定できる(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        bench = _create(repo, "ベンチプレス")
        add_training_max(repo, uid=bench.exercise.uid, value=100.0, reason="初期値")
        shoulder_press = _create(repo, "ショルダープレス")

        updated = _update(repo, shoulder_press.exercise.uid, "ショルダープレス", parent_uid=bench.exercise.uid)

        assert updated.exercise.parent_id == bench.exercise.id
        assert repo.get(shoulder_press.exercise.uid).parent_id == bench.exercise.id

    def test_TM_の履歴がある種目に派生元を設定できず派生元は変わらない(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        bench = _create(repo, "ベンチプレス")
        shoulder_press = _create(repo, "ショルダープレス")
        add_training_max(repo, uid=shoulder_press.exercise.uid, value=60.0, reason="初期値")

        with pytest.raises(BusinessRuleViolation, match="^トレーニングマックスの履歴がある種目は派生種目にできません$"):
            _update(repo, shoulder_press.exercise.uid, "ショルダープレス", parent_uid=bench.exercise.uid)

        assert repo.get(shoulder_press.exercise.uid).parent_id is None

    def test_派生種目を持つ種目に派生元を設定できず派生元は変わらない(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        bench = _create(repo, "ベンチプレス")
        _create(repo, "ポーズベンチ", parent_uid=bench.exercise.uid, coefficient=0.87)
        shoulder_press = _create(repo, "ショルダープレス")

        with pytest.raises(BusinessRuleViolation, match="^派生種目を持つ種目は派生種目にできません$"):
            _update(repo, bench.exercise.uid, "ベンチプレス", parent_uid=shoulder_press.exercise.uid)

        assert repo.get(bench.exercise.uid).parent_id is None

    def test_既存の別の種目と同じ名前に変更すると固定の文言で_Conflict(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        _create(repo, "ベンチプレス")
        squat = _create(repo, "スクワット")

        with pytest.raises(Conflict, match="^同じ名前の種目があります$"):
            _update(repo, squat.exercise.uid, "ベンチプレス", parent_uid=None)
