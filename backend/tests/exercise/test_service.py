import pytest
from sqlalchemy.orm import Session

from common.errors import BusinessRuleViolation
from features.exercise.repository import DbExerciseRepository
from features.exercise.service import change_training_max, create_exercise


class TestChangeTrainingMax:
    def test_派生種目には_TM_を登録できない(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        bench = create_exercise(
            repo,
            name="ベンチプレス",
            parent_uid=None,
            coefficient=None,
            e1rm_divisor=40.0,
            increment_kg=2.5,
            default_rest_seconds=180,
        )
        pause_bench = create_exercise(
            repo,
            name="ポーズベンチ",
            parent_uid=bench.exercise.uid,
            coefficient=0.87,
            e1rm_divisor=None,
            increment_kg=2.5,
            default_rest_seconds=180,
        )

        with pytest.raises(BusinessRuleViolation, match="^派生種目にはトレーニングマックスを登録できません$"):
            change_training_max(repo, uid=pause_bench.exercise.uid, value=80.0, reason="入力")
