from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from common.errors import Conflict
from features.exercise.repository import DbExerciseRepository
from features.exercise.types import ExerciseFields, TrainingMax, TrainingMaxSource

SQUAT = ExerciseFields(
    name="スクワット", parent_id=None, coefficient=None, e1rm_divisor=33.3, increment_kg=2.5, default_rest_seconds=180
)


class TestCreate:
    def test_同じ名前の種目があれば固定の文言で_Conflict(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        repo.create(uid="squat-1", fields=SQUAT)

        with pytest.raises(Conflict, match="^同じ名前の種目があります$"):
            repo.create(uid="squat-2", fields=SQUAT)


class TestListTrainingMaxes:
    def test_手動で変更した行が履歴の先頭に並ぶ(self, db_session: Session) -> None:
        repo = DbExerciseRepository(db_session)
        squat = repo.create(uid="squat", fields=SQUAT)
        repo.add_training_max(
            TrainingMax(
                exercise_id=squat.id,
                value=125.0,
                effective_at=datetime(2026, 10, 5, 0, 0, tzinfo=UTC),
                source=TrainingMaxSource.auto,
                reason="週ごとの自動更新",
            )
        )
        repo.add_training_max(
            TrainingMax(
                exercise_id=squat.id,
                value=122.5,
                effective_at=datetime(2026, 10, 14, 0, 0, tzinfo=UTC),
                source=TrainingMaxSource.manual,
                reason="腰の違和感で2週間落とす",
            )
        )

        history = [(training_max.value, training_max.source) for training_max in repo.list_training_maxes()]

        assert history == [(122.5, TrainingMaxSource.manual), (125.0, TrainingMaxSource.auto)]
