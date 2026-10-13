from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.db.entities import ExerciseSetRow, PerformedExerciseRow
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

    def test_セットをすべて消して保存すると読み直してもセットは無い(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        _create_log(db_session)
        repo.replace_sets("performed", sets=[ExerciseSet(order=1, weight=75.0, reps=5, rir=2)])

        repo.replace_sets("performed", sets=[])
        db_session.expire_all()

        assert repo.get("log").exercises[0].sets == ()


class TestDelete:
    def test_削除すると種目とセットも消えカレンダーに出ない(self, db_session: Session) -> None:
        repo = DbTrainingLogRepository(db_session)
        _create_log(db_session)
        repo.replace_sets("performed", sets=[ExerciseSet(order=1, weight=75.0, reps=5, rir=2)])

        repo.delete("log")

        performed_count = db_session.execute(select(func.count()).select_from(PerformedExerciseRow)).scalar_one()
        set_count = db_session.execute(select(func.count()).select_from(ExerciseSetRow)).scalar_one()
        calendar = repo.list_between(date(2026, 9, 28), date(2026, 11, 1))
        assert (calendar, performed_count, set_count) == ([], 0, 0)
