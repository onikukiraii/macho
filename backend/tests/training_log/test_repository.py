from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.db.entities import ExerciseSetRow, PerformedExerciseRow
from common.errors import Conflict
from features.exercise.repository import DbExerciseRepository
from features.exercise.types import ExerciseFields
from features.training_log.repository import DbTrainingLogRepository
from features.training_log.types import ExerciseSet, NewPerformedExercise, TrainingLog


def _create_log(db_session: Session) -> TrainingLog:
    fields = ExerciseFields(
        name="ベンチプレス",
        parent_id=None,
        coefficient=None,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        default_rest_seconds=180,
    )
    exercise = DbExerciseRepository(db_session).create(uid="bench", fields=fields)
    return DbTrainingLogRepository(db_session).create(
        uid="log",
        date=date(2026, 10, 13),
        program_day_id=None,
        exercises=[NewPerformedExercise(uid="performed", exercise_id=exercise.id, planned_exercise_id=None, order=1)],
    )


class TestReplaceSets:
    def test_保存し直すと前のセットは置き換わり同じ番号で読み直せる(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        _create_log(db_session)
        repo.replace_sets(
            "performed",
            sets=[ExerciseSet(order=order, weight=75.0, reps=5, rir=2) for order in (1, 2, 3)],
        )

        repo.replace_sets(
            "performed",
            sets=[ExerciseSet(order=1, weight=77.5, reps=5, rir=1), ExerciseSet(order=3, weight=77.5, reps=4, rir=0)],
        )
        db_session.expire_all()

        assert repo.get("log").exercises[0].sets == (
            ExerciseSet(order=1, weight=77.5, reps=5, rir=1),
            ExerciseSet(order=3, weight=77.5, reps=4, rir=0),
        )

    def test_同じ番号のセットは保存できず前のセットが残る(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        _create_log(db_session)
        repo.replace_sets("performed", sets=[ExerciseSet(order=1, weight=75.0, reps=5, rir=2)])

        with pytest.raises(Conflict):
            repo.replace_sets(
                "performed",
                sets=[
                    ExerciseSet(order=1, weight=77.5, reps=5, rir=1),
                    ExerciseSet(order=1, weight=77.5, reps=4, rir=0),
                ],
            )

        db_session.expire_all()
        assert repo.get("log").exercises[0].sets == (ExerciseSet(order=1, weight=75.0, reps=5, rir=2),)

    def test_セットをすべて消して保存すると読み直してもセットは無い(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        _create_log(db_session)
        repo.replace_sets("performed", sets=[ExerciseSet(order=1, weight=75.0, reps=5, rir=2)])

        repo.replace_sets("performed", sets=[])
        db_session.expire_all()

        assert repo.get("log").exercises[0].sets == ()


class TestUpdatePerformedExercise:
    def test_差し替えは種目だけを更新しメモは変わらない(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        _create_log(db_session)
        repo.update_performed_exercise_memo("performed", memo="肩に違和感")
        squat = DbExerciseRepository(db_session).create(
            uid="squat",
            fields=ExerciseFields(
                name="スクワット",
                parent_id=None,
                coefficient=None,
                e1rm_divisor=40.0,
                increment_kg=5.0,
                default_rest_seconds=180,
            ),
        )

        repo.replace_performed_exercise("performed", exercise_id=squat.id)
        db_session.expire_all()

        exercise = repo.get("log").exercises[0]
        assert (exercise.exercise_id, exercise.memo) == (squat.id, "肩に違和感")

    def test_メモの保存はメモだけを更新し種目は変わらない(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        before = _create_log(db_session).exercises[0]

        repo.update_performed_exercise_memo("performed", memo="肩に違和感")
        db_session.expire_all()

        exercise = repo.get("log").exercises[0]
        assert (exercise.exercise_id, exercise.memo) == (before.exercise_id, "肩に違和感")


class TestDelete:
    def test_削除すると種目とセットも消えカレンダーに出ず別の記録は残る(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        log = _create_log(db_session)
        repo.replace_sets("performed", sets=[ExerciseSet(order=1, weight=75.0, reps=5, rir=2)])
        repo.create(
            uid="other",
            date=date(2026, 10, 9),
            program_day_id=None,
            exercises=[
                NewPerformedExercise(
                    uid="other-performed", exercise_id=log.exercises[0].exercise_id, planned_exercise_id=None, order=1
                )
            ],
        )
        repo.replace_sets("other-performed", sets=[ExerciseSet(order=1, weight=72.5, reps=5, rir=2)])

        repo.delete("log")

        performed_count = db_session.execute(select(func.count()).select_from(PerformedExerciseRow)).scalar_one()
        set_count = db_session.execute(select(func.count()).select_from(ExerciseSetRow)).scalar_one()
        calendar = repo.list_between(from_date=date(2026, 9, 28), to_date=date(2026, 11, 1))
        assert ([training_log.uid for training_log in calendar], performed_count, set_count) == (["other"], 1, 1)
